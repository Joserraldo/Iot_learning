#!/usr/bin/env python3
"""
vm_push.py — Sube el código del Lab 4 a la VM de Azure por SFTP (paramiko).

Sube python/, requirements.txt, README.md y .env (el .env NUNCA va a git,
pero sí a la VM para que los clientes lean las credenciales de un lado).

Uso:
  python tools/vm_push.py                 # usa VM_HOST/VM_USER/VM_PASS del .env
  python tools/vm_push.py --check         # solo prueba conexión
"""

import argparse
import os
import sys
from pathlib import Path

import paramiko
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
FILES = [
    "python/common.py",
    "python/amqp_sdk.py",
    "python/coap_client.py",
    "python/coap_gateway.py",
    "python/provision_devices.py",
    "python/mqtt_baseline.py",
    "requirements.txt",
    "README.md",
    ".env.example",
]
ENV_FILE = ".env"


def redact(s: str) -> str:
    return (s[:4] + "…") if s else "(vacío)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.getenv("VM_HOST", "52.237.172.24"))
    ap.add_argument("--user", default=os.getenv("VM_USER", "azureuser"))
    ap.add_argument("--pass", dest="password", default=os.getenv("VM_PASS"))
    ap.add_argument("--remote-dir", default="~/taller_4_iot")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    pw = args.password or os.getenv("VM_PASS")
    if not pw:
        print("Falta VM_PASS en .env o --pass")
        sys.exit(1)

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(args.host, username=args.user, password=pw, timeout=25)
    print(f"Conectado {args.user}@{args.host}")

    if args.check:
        si, so, se = c.exec_command("python3 --version && hostname && nproc && free -m | head -2")
        print(so.read().decode())
        c.close()
        return

    remote_dir = args.remote_dir.replace("~", "/home/" + args.user)
    si, so, se = c.exec_command(f"mkdir -p {remote_dir}/python {remote_dir}/evidencias/{'amqp coap comparativa'.replace(' ', '/ ')} 2>/dev/null; mkdir -p {remote_dir}/evidencias/amqp {remote_dir}/evidencias/coap {remote_dir}/evidencias/comparativa {remote_dir}/tools {remote_dir}/docs && echo OK")
    print(so.read().decode().strip())

    sftp = c.open_sftp()
    for rel in FILES:
        local = ROOT / rel
        if not local.exists():
            print(f"SKIP (no existe): {rel}")
            continue
        remote = f"{remote_dir}/{rel}"
        sftp.put(str(local), remote)
        print(f"subido: {rel}")
    if (ROOT / ENV_FILE).exists():
        sftp.put(str(ROOT / ENV_FILE), f"{remote_dir}/{ENV_FILE}")
        print(f"subido: {ENV_FILE} (permisos 600)")
        c.exec_command(f"chmod 600 {remote_dir}/{ENV_FILE}")
    sftp.close()

    si, so, se = c.exec_command(f"ls -la {remote_dir} {remote_dir}/python | head -30")
    print(so.read().decode())
    c.close()
    print("Push completo.")


if __name__ == "__main__":
    main()
