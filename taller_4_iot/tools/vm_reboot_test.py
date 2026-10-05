#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vm_reboot_test.py — prueba de reinicio: demuestra que TODO vuelve solo.

Reinicia la VM y comprueba, sin tocar nada más:
  1. que HTTPS responde otra vez (nginx),
  2. que el servicio del dashboard volvió (systemd enabled),
  3. que los 3 protocolos se relanzaron solos (vigilante + estado en disco) y están publicando,
  4. que el swap sigue montado.
Se usa una vez para validar la resiliencia; no es parte del flujo normal.
"""
import os
import sys
import time
from pathlib import Path

import paramiko
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DOMINIO = "iotcentraljose.duckdns.org"


def su(c, cmd, pw, timeout=300):
    si, so, se = c.exec_command(f"sudo -S -p '' bash -c {cmd!r}", timeout=timeout)
    si.write(pw + "\n")
    si.flush()
    return si.channel.recv_exit_status(), so.read().decode(errors="replace"), se.read().decode(errors="replace")


def sh(c, cmd, timeout=120):
    si, so, se = c.exec_command(cmd, timeout=timeout)
    return si.channel.recv_exit_status(), so.read().decode(errors="replace").strip(), \
        se.read().decode(errors="replace").strip()


def conectar(host, user, pw, intentos=1):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, username=user, password=pw, timeout=20)
    return c


def main():
    load_dotenv(ROOT / ".env")
    host = os.getenv("VM_HOST", "52.237.172.24")
    user = os.getenv("VM_USER", "azureuser")
    pw = os.getenv("VM_PASS")
    if not pw:
        print("Falta VM_PASS")
        sys.exit(1)

    c = conectar(host, user, pw)
    rc, out, err = sh(c, "uptime -p; who -b 2>/dev/null | head -1")
    print("antes:", out)
    print("reiniciando…")
    try:
        su(c, "systemctl reboot", pw, 30)
    except Exception:
        pass
    c.close()

    # esperar a que vuelva
    t0 = time.time()
    listo = False
    while time.time() - t0 < 240:
        time.sleep(10)
        try:
            c = conectar(host, user, pw)
            rc, out, _ = sh(c, "echo vivo")
            if out == "vivo":
                listo = True
                break
        except Exception:
            continue
    if not listo:
        print("❌ la VM no volvió en 4 minutos")
        sys.exit(1)
    print(f"✅ SSH volvió a los {int(time.time()-t0)} s")

    rc, out, _ = sh(c, "uptime -p; systemctl is-active nginx taller4-dashboard; "
                       "systemctl is-enabled nginx taller4-dashboard; swapon --show=NAME,SIZE --noheadings")
    print(out)

    print("esperando 45 s a que el vigilante relance los protocolos…")
    time.sleep(45)
    rc, out, _ = sh(c, "cd ~/taller_4_iot && "
                       "curl -s -m 10 http://127.0.0.1:8080/api/estado | .venv/bin/python -c "
                       "\"import sys,json;d=json.load(sys.stdin);"
                       "print({k:(v['corriendo'], v['metrica']['total'], v['reinicios']) "
                       "for k,v in d['protocolos'].items()}, 'gw:', d['protocolos']['coap']['gateway']['corriendo'])\"; "
                       "echo '--- vigilante ---'; tail -8 evidencias/autoreinicio.log; "
                       "echo '--- procesos ---'; pgrep -af 'python/(mqtt|amqp|coap)' | wc -l")
    print(out)
    c.close()
    print("\ncomprobación externa:")
    print(os.popen(f'curl -s -m 20 -o NUL -w "https://{DOMINIO}/ -> %{{http_code}}\\n" https://{DOMINIO}/').read())


if __name__ == "__main__":
    main()
