#!/usr/bin/env python3
"""vm_sync.py — sube el arbol del taller 5 (docker/, python/, dashboard/) a la
VM por SFTP y lo VERIFICA con un grep que solo existe en la version nueva.
Subtree del patron de tools/vm_push.py del taller 4.
Uso: python tools/vm_sync.py [--remote-dir ~/taller_5_iot]
"""
import argparse
import os
import sys
from pathlib import Path

import paramiko
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DIRS = ["docker", "python", "dashboard"]
SKIP_NAMES = {"__pycache__", ".hermes"}
VERIFY = {  # remote relative path -> token que SOLO tiene la version nueva
    "docker/docker-compose.yml": "taller5-grafana",
    "python/publisher.py": "lab5-publisher",
    "python/ingest.py": "to_line_protocol",
    "docker/grafana/dashboards/lab5.json": "lab5",
}


def walk(d: Path):
    for p in sorted(d.rglob("*")):
        if p.is_file() and not (SKIP_NAMES & set(p.parts)):
            yield p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remote-dir", default="~/taller_5_iot")
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
    sftp = c.open_sftp()

    # resolver ~ y crear estructura
    home = sftp.normalize(".")
    rbase = args.remote_dir.replace("~", home)
    made = set()
    files = []
    for d in DIRS:
        local = ROOT / d
        if not local.exists():
            continue
        for p in walk(local):
            rel = p.relative_to(ROOT).as_posix()
            files.append((p, rel))
            remote_file = f"{rbase}/{rel}"
            remote_parent = remote_file.rsplit("/", 1)[0]
            parts = remote_parent.split("/")
            for i in range(3, len(parts) + 1):  # salta raiz absoluta rara
                frag = "/".join(parts[:i])
                if frag and frag not in made:
                    try:
                        sftp.stat(frag)
                    except IOError:
                        sftp.mkdir(frag)
                    made.add(frag)
    for p, rel in files:
        sftp.put(str(p), f"{rbase}/{rel}")
        print(f"subido: {rel}")
    try:
        sftp.stat(f"{rbase}/evidencias")
    except IOError:
        sftp.mkdir(f"{rbase}/evidencias")
    sftp.close()

    # VERIFICAR en la VM que lo que aterrizo es la version nueva (no confiar
    # en la linea "subido:" — leccion del skill remote-vm-service-ops)
    ok = True
    for rel, token in VERIFY.items():
        _, so, _ = c.exec_command(
            f"grep -c '{token}' {rbase}/{rel}", timeout=20)
        out = so.read().decode().strip()
        good = out.isdigit() and int(out) > 0
        ok = ok and good
        print(f"verificado {rel}: {'OK' if good else 'FALTA ' + token + ' -> ' + out}")
    c.close()
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
