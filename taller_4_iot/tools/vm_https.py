#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vm_https.py — deja el dashboard servido en el dominio con HTTPS real (una sola vez).

Qué hace, en la VM (usa sudo con la contraseña de .env, vía stdin):
  1. Instala nginx + certbot (apt).
  2. Publica el site `iotcentraljose.duckdns.org` -> proxy a 127.0.0.1:8080.
  3. Desactiva el site por defecto de nginx.
  4. Pide el certificado a Let's Encrypt con certbot --nginx (reto HTTP-01, puerto 80)
     y activa el redirect http -> https. La renovación queda en un timer de systemd.
  5. Verifica: nginx -t, HTTP 301 en el puerto 80, HTTPS 200 en el 443.

Uso:
  python tools/vm_https.py                 # instala y configura
  python tools/vm_https.py --solo-verificar
"""
import argparse
import os
import sys
import time
from pathlib import Path

import paramiko
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DOMINIO = "iotcentraljose.duckdns.org"
CONF_REMOTO = "/home/azureuser/taller_4_iot/nginx-iotcentraljose.conf"

NGINX_CONF = f"""# {DOMINIO} -> dashboard Lab 4 (gunicorn en 127.0.0.1:8080)
server {{
    listen 80;
    listen [::]:80;
    server_name {DOMINIO};

    client_max_body_size 20m;

    location / {{
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;      # /api/evidencia genera gráficas
        proxy_buffering off;
    }}
}}
"""


def su(c, cmd, pw, timeout=900):
    """Ejecuta un comando con sudo escribiendo la contraseña por stdin (nunca en la línea)."""
    si, so, se = c.exec_command(f"sudo -S -p '' bash -c {cmd!r}", timeout=timeout, get_pty=False)
    si.write(pw + "\n")
    si.flush()
    out = so.read().decode(errors="replace")
    err = se.read().decode(errors="replace")
    rc = si.channel.recv_exit_status()
    return rc, out.strip(), err.strip()


def sh(c, cmd, timeout=300):
    si, so, se = c.exec_command(cmd, timeout=timeout)
    out = so.read().decode(errors="replace")
    err = se.read().decode(errors="replace")
    return si.channel.recv_exit_status(), out.strip(), err.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.getenv("VM_HOST", "52.237.172.24"))
    ap.add_argument("--user", default=os.getenv("VM_USER", "azureuser"))
    ap.add_argument("--pass", dest="password", default=os.getenv("VM_PASS"))
    ap.add_argument("--solo-verificar", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="prueba la renovación del certificado sin tocar el que está en uso")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    pw = args.password or os.getenv("VM_PASS")
    if not pw:
        print("Falta VM_PASS en .env o --pass")
        sys.exit(1)

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(args.host, username=args.user, password=pw, timeout=25)
    print(f"conectado {args.user}@{args.host}")

    if args.dry_run:
        rc, out, err = su(c, "certbot renew --dry-run 2>&1 | tail -14", pw, 600)
        print(out.strip() or err.strip())
        c.close()
        return

    if not args.solo_verificar:
        rc, out, err = su(c, "DEBIAN_FRONTEND=noninteractive apt-get update -q", pw)
        print("apt-get update:", (out or err)[-300:])
        rc, out, err = su(c, "DEBIAN_FRONTEND=noninteractive apt-get install -y -q nginx certbot python3-certbot-nginx", pw)
        print("apt-get install:", (out or err)[-300:])

        # publicar el site
        sftp = c.open_sftp()
        with sftp.open(CONF_REMOTO, "w") as f:
            f.write(NGINX_CONF)
        sftp.close()
        print(f"config nginx subida a {CONF_REMOTO}")
        rc, out, err = su(c, "cp /home/azureuser/taller_4_iot/nginx-iotcentraljose.conf "
                            "/etc/nginx/sites-available/iotcentraljose && "
                            "ln -sf /etc/nginx/sites-available/iotcentraljose /etc/nginx/sites-enabled/iotcentraljose && "
                            "rm -f /etc/nginx/sites-enabled/default && nginx -t", pw)
        print("nginx -t:", out or err)
        if rc != 0:
            print("nginx -t falló; se aborta")
            c.close()
            sys.exit(1)
        rc, out, err = su(c, "systemctl enable --now nginx && systemctl reload nginx && "
                            "systemctl is-active nginx", pw)
        print("nginx:", out or err)
        time.sleep(2)

        rc, out, err = su(c, f"certbot --nginx -d {DOMINIO} --non-interactive --agree-tos "
                             f"--register-unsafely-without-email --redirect --keep-until-expiring", pw)
        print("certbot:", (out or err)[-700:])
        if "Congratulations" not in (out + err) and "not yet due for renewal" not in (out + err) \
                and "Successfully deployed" not in (out + err):
            print("⚠ certbot no reportó éxito; revisa el detalle de arriba")

    # ---- verificación
    print("\n=== verificación ===")
    rc, out, err = su(c, f"certbot certificates 2>/dev/null | grep -E 'Certificate Name|Domains|Expiry'", pw)
    print(out or err)
    rc, out, err = sh(c, "curl -s -o /dev/null -w 'http://%(dominio)s  -> %{http_code} (esperado 301)\\n' "
                         f"-H 'Host: {DOMINIO}' http://127.0.0.1/ ; "
                         f"curl -sk -o /dev/null -w 'https://{DOMINIO} -> %{{http_code}} (esperado 200)\\n' "
                         f"-H 'Host: {DOMINIO}' https://127.0.0.1/ ; "
                         f"curl -sk -o /dev/null -w 'https api /api/estado   -> %{{http_code}}\\n' "
                         f"-H 'Host: {DOMINIO}' https://127.0.0.1/api/estado")
    print(out or err)
    rc, out, err = sh(c, "systemctl list-timers 'certbot*' --no-pager | head -3")
    print(out or err)
    c.close()


if __name__ == "__main__":
    main()
