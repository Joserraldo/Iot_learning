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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", help="comando a ejecutar en la VM")
    ap.add_argument("--host", default=os.getenv("VM_HOST", "52.237.172.24"))
    ap.add_argument("--user", default=os.getenv("VM_USER", "azureuser"))
    ap.add_argument("--pass", dest="password", default=os.getenv("VM_PASS"))
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    pw = args.password or os.getenv("VM_PASS")
    if not pw:
        print("Falta VM_PASS en .env")
        sys.exit(1)

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(args.host, username=args.user, password=pw, timeout=25)
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
