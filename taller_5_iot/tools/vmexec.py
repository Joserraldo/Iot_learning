#!/usr/bin/env python3
"""vmexec.py — ejecuta un comando en la VM (paramiko) y muestra stdout/stderr.
Uso: python tools/vmexec.py "comando" [--timeout 60] [--sudo]
"""
import argparse
import os
import sys
from pathlib import Path
import paramiko
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def connect(client):
    """Conecta con key (VM_KEY del .env) o password (VM_PASS)."""
    load_dotenv(ROOT / ".env")
    host = os.getenv("VM_HOST", "52.159.94.196")
    user = os.getenv("VM_USER", "azureuser")
    key = os.getenv("VM_KEY")
    pw = os.getenv("VM_PASS")
    if not (key or pw):
        print("Falta VM_KEY o VM_PASS en .env")
        sys.exit(1)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if key:
        k = paramiko.RSAKey.from_private_key_file(str(ROOT / key))
        client.connect(host, username=user, pkey=k, timeout=25)
    else:
        client.connect(host, username=user, password=pw, timeout=25)
    return host, user


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", help="comando a ejecutar en la VM")
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()

    c = paramiko.SSHClient()
    connect(c)
    si, so, se = c.exec_command(args.cmd, timeout=args.timeout)
    status = si.channel.recv_exit_status()
    out = so.read().decode(errors="replace")
    err = se.read().decode(errors="replace")
    if out:
        print(out)
    if err:
        sys.stderr.write(err)
    c.close()
    sys.exit(0 if status == 0 else 1)


if __name__ == "__main__":
    main()
