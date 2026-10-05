#!/usr/bin/env python3
"""vm_pull.py — baja evidencias de la VM (SFTP) a evidencias/ local.
Uso: python tools/vm_pull.py [--all]   (sin args: solo vm-*.jsonl formales)
"""
import argparse
import os
import sys
from pathlib import Path
import paramiko
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
REMOTE_DIR = "/home/azureuser/taller_4_iot/evidencias"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="baja TODOS los archivos de evidencias")
    ap.add_argument("--host", default=os.getenv("VM_HOST", "52.237.172.24"))
    ap.add_argument("--user", default=os.getenv("VM_USER", "azureuser"))
    ap.add_argument("--pass", dest="password", default=os.getenv("VM_PASS"))
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    pw = args.password or os.getenv("VM_PASS")
    if not pw:
        print("Falta VM_PASS en .env")
        sys.exit(1)

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(args.host, username=args.user, password=pw, timeout=25)
    sftp = c.open_sftp()

    local_base = ROOT / "evidencias"
    downloaded = []
    for proto in ("mqtt", "amqp", "coap"):
        rdir = f"{REMOTE_DIR}/{proto}"
        try:
            for entry in sftp.listdir_attr(rdir):
                if entry.st_mode and entry.st_size == 0:
                    continue
                rfile = f"{rdir}/{entry.filename}"
                if not args.all and not entry.filename.startswith("vm-"):
                    continue
                if not (args.all or "formal" in entry.filename or "run" in entry.filename or "diag" in entry.filename):
                    continue
                ldir = local_base / proto
                ldir.mkdir(parents=True, exist_ok=True)
                lfile = ldir / entry.filename
                sftp.get(rfile, str(lfile))
                downloaded.append(f"{proto}/{entry.filename}")
        except FileNotFoundError:
            pass
    sftp.close()
    c.close()
    for f in downloaded:
        print(f"bajado: {f}")
    print(f"Total: {len(downloaded)}")


if __name__ == "__main__":
    main()
