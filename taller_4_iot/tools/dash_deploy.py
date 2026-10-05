#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dash_deploy.py — despliega/actualiza el dashboard del Lab 4 en la VM de Azure.

Qué hace:
  1. Sube dashboard/ (dashboard.py, hacer_graficas.py, templates/) a ~/taller_4_iot/dashboard/
  2. Instala en el venv lo que falte: flask, matplotlib, gunicorn
  3. Genera DASH_KEY (si no existe) y la añade al .env de la VM
  4. Instala/actualiza el servicio systemd `taller4-dashboard` (gunicorn en 127.0.0.1:8080)
     y lo reinicia; antes mata una instancia vieja lanzada con setsid, si la hay
  5. Verifica: servicio activo, HTTP local 200 y HTTPS por el dominio (si nginx está puesto)

El HTTPS se configura una sola vez con `python tools/vm_https.py`.

Uso (desde el repo local, con el Python que tiene paramiko: C:\\Program Files\\Python313\\python.exe):
  python tools/dash_deploy.py                 # sube + instala + reinicia + verifica
  python tools/dash_deploy.py --no-reiniciar  # solo sube/instala
  python tools/dash_deploy.py --clave MI_CLAVE
"""
import argparse
import os
import secrets
import sys
from pathlib import Path

import paramiko
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
REMOTE = "/home/azureuser/taller_4_iot"
DOMINIO = "iotcentraljose.duckdns.org"
SERVICIO = "taller4-dashboard"
ARCHIVOS = [
    "dashboard/dashboard.py",
    "dashboard/hacer_graficas.py",
    "dashboard/templates/index.html",
    "dashboard/templates/informe.html",
    "dashboard/templates/_diagrama.html",
]
UNIT = f"""[Unit]
Description=Sala de control Lab 4 IoT (MQTT / AMQP / CoAP) - dashboard Flask+gunicorn
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=azureuser
# Al reiniciar/actualizar SOLO el dashboard, los clientes de los protocolos no se tocan
# (si no, un redespliegue cortaba la corrida y el vigilante tenía que relanzarlos).
KillMode=process
Group=azureuser
WorkingDirectory={REMOTE}/dashboard
Environment=PYTHONUNBUFFERED=1
Environment=HOME=/home/azureuser
# Red de seguridad en una VM de 896 MB: si la app se dispara, systemd la limita
# (con desbordamiento a swap) en vez de dejar sin memoria a toda la máquina.
MemoryMax=450M
MemorySwapMax=1G
# El dashboard lee DASH_KEY y el resto de credenciales del .env con python-dotenv
# --max-requests: recicla cada worker de vez en cuando para que no acumule memoria en meses
ExecStart={REMOTE}/.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8080 --timeout 300 --graceful-timeout 30 --max-requests 3000 --max-requests-jitter 300 --access-logfile - dashboard:APP
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""


def sh(c, cmd, timeout=600):
    si, so, se = c.exec_command(cmd, timeout=timeout)
    out = so.read().decode(errors="replace")
    err = se.read().decode(errors="replace")
    return si.channel.recv_exit_status(), out.strip(), err.strip()


def su(c, cmd, pw, timeout=600):
    """sudo sin exponer la contraseña en la línea de comandos (va por stdin)."""
    si, so, se = c.exec_command(f"sudo -S -p '' bash -c {cmd!r}", timeout=timeout)
    si.write(pw + "\n")
    si.flush()
    out = so.read().decode(errors="replace")
    err = se.read().decode(errors="replace")
    return si.channel.recv_exit_status(), out.strip(), err.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.getenv("VM_HOST", "52.237.172.24"))
    ap.add_argument("--user", default=os.getenv("VM_USER", "azureuser"))
    ap.add_argument("--pass", dest="password", default=os.getenv("VM_PASS"))
    ap.add_argument("--clave", default=None, help="DASH_KEY a fijar")
    ap.add_argument("--no-reiniciar", action="store_true")
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

    rc, out, err = sh(c, f"mkdir -p {REMOTE}/dashboard/templates && echo OK")
    print(out or err)

    sftp = c.open_sftp()
    for rel in ARCHIVOS:
        local = ROOT / rel
        if not local.exists():
            print(f"FALTA en local: {rel}")
            continue
        sftp.put(str(local), f"{REMOTE}/{rel}")
        print(f"subido: {rel}")
    with sftp.open(f"{REMOTE}/{SERVICIO}.service", "w") as f:
        f.write(UNIT)
    sftp.close()

    # --- dependencias en el venv
    prog = ('import flask, matplotlib, gunicorn; print("flask", flask.__version__, '
            '"| matplotlib", matplotlib.__version__, "| gunicorn", gunicorn.__version__)')
    rc, out, err = sh(c, f"cd {REMOTE} && .venv/bin/pip install -q flask matplotlib gunicorn "
                         f"2>&1 | tail -3; .venv/bin/python -c '{prog}'", timeout=900)
    print(out or err)

    # --- clave de control
    clave = args.clave
    rc, out, _ = sh(c, f"grep -c '^DASH_KEY=' {REMOTE}/.env || true")
    ya = out.strip() not in ("", "0")
    if not clave and not ya:
        clave = secrets.token_urlsafe(12)
    if clave:
        sh(c, f"sed -i '/^DASH_KEY=/d' {REMOTE}/.env; "
              f"printf '\\nDASH_KEY={clave}\\n' >> {REMOTE}/.env; chmod 600 {REMOTE}/.env")
        print(f"DASH_KEY fijada en la VM: {clave}")
    else:
        rc, out, _ = sh(c, f"grep '^DASH_KEY=' {REMOTE}/.env")
        print(f"(clave ya existente) {out.strip()}")

    if args.no_reiniciar:
        c.close()
        print("Listo (sin reiniciar el servicio).")
        return

    # --- parada limpia: primero una instancia vieja de la época de setsid (si quedara),
    #     luego `systemctl stop` para que systemd suelte el :8080 sin matar el master a lo bruto
    #     (matarlo con -9 dejaba workers colgados un rato con el candado del vigilante tomado).
    sh(c, f"OLD=$(cat {REMOTE}/evidencias/dashboard.pid 2>/dev/null); [ -n \"$OLD\" ] && kill -9 $OLD 2>/dev/null; "
          f"rm -f {REMOTE}/evidencias/dashboard.pid; "
          f"systemctl stop {SERVICIO} 2>/dev/null; sleep 2; "
          f"QUIEN=$(ss -ltnp 2>/dev/null | grep ':8080' | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1); "
          f"[ -n \"$QUIEN\" ] && kill -9 $QUIEN 2>/dev/null; "
          f"sleep 1; true")

    # --- servicio systemd
    rc, out, err = su(c, f"cp {REMOTE}/{SERVICIO}.service /etc/systemd/system/{SERVICIO}.service && "
                         f"systemctl daemon-reload && systemctl enable {SERVICIO} >/dev/null 2>&1 && "
                         f"systemctl restart {SERVICIO} && sleep 4 && systemctl is-active {SERVICIO}", pw)
    print("systemd:", out or err)

    rc, out, err = sh(c, "sleep 2; "
                         "curl -s -m 10 -o /dev/null -w 'local  http://127.0.0.1:8080/api/estado -> HTTP %{http_code}\\n' "
                         "http://127.0.0.1:8080/api/estado; "
                         f"curl -sk -m 10 -o /dev/null -w 'https  https://{DOMINIO}/api/estado      -> HTTP %{{http_code}}\\n' "
                         f"-H 'Host: {DOMINIO}' https://127.0.0.1/api/estado; "
                         f"echo '--- ultimas lineas del servicio {SERVICIO} ---'; "
                         f"journalctl -u {SERVICIO} -n 6 --no-pager | tail -6")
    print(out or err)
    if err:
        print("stderr:", err)
    c.close()


if __name__ == "__main__":
    main()
