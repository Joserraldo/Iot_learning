#!/usr/bin/env python3
"""vmsudo.py — ejecuta UN comando como root en la VM (paramiko).
La contraseña se envia por stdin a `sudo -S -p ''` (nunca aparece en ps,
en el cmdline remoto ni en logs). Uso: python tools/vmsudo.py "<cmd>" [--timeout 900]
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
    ap.add_argument("cmd")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    host = os.getenv("VM_HOST", "52.159.94.196")
    user = os.getenv("VM_USER", "azureuser")
    key = os.getenv("VM_KEY")
    pw = os.getenv("VM_PASS")

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if key:
        k = paramiko.RSAKey.from_private_key_file(str(ROOT / key))
        c.connect(host, username=user, pkey=k, timeout=25)
    else:
        c.connect(host, username=user, password=pw, timeout=25)
    si, so, se = c.exec_command(
        "sudo -S -p '' bash -c " + repr(args.cmd), timeout=args.timeout)
    if not key:
        si.write(pw + "\n")
    si.flush()
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
