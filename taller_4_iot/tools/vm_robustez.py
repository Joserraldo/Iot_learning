#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vm_robustez.py — deja la VM lista para aguantar meses de demostraciones (una sola vez).

Qué hace (con sudo, la contraseña va por stdin, nunca en la línea de comandos):
  1. **Swap de 2 GB**: la VM (B2ats_v2, 896 MB de RAM) no tiene swap; una captura con
     matplotlib puede pedir ~120 MB de golpe y sin swap el OOM killer mata procesos.
     Queda en /etc/fstab, así que sobrevive reinicios.
  2. **limita el journal de systemd** a 200 MB (por defecto puede crecer al 10 % del disco,
     y aquí cada refresco de la página genera una línea de log de nginx/gunicorn).
  3. **vm.swappiness=10**: que no empiece a usar swap por gusto, solo como red de seguridad.
  4. Comprueba logrotate de nginx y que unattended-upgrades no reinicie la VM solo.

Uso:  python tools/vm_robustez.py            (idempotente, se puede repetir)
"""
import argparse
import os
import sys
from pathlib import Path

import paramiko
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
REMOTE = "/home/azureuser/taller_4_iot"

JOURNALD = """[Journal]
# Límite puesto para el lab 4: el servidor pequeño no debe llenarse de logs
SystemMaxUse=200M
SystemKeepFree=1G
RuntimeMaxUse=64M
MaxRetentionSec=1month
"""

SYSCTL = """# Lab 4 - servidor pequeño: usar swap solo como red de seguridad
vm.swappiness=10
"""


def su(c, cmd, pw, timeout=900):
    si, so, se = c.exec_command(f"sudo -S -p '' bash -c {cmd!r}", timeout=timeout)
    si.write(pw + "\n")
    si.flush()
    out = so.read().decode(errors="replace")
    err = se.read().decode(errors="replace")
    return si.channel.recv_exit_status(), out.strip(), err.strip()


def sh(c, cmd, timeout=300):
    si, so, se = c.exec_command(cmd, timeout=timeout)
    return si.channel.recv_exit_status(), so.read().decode(errors="replace").strip(), \
        se.read().decode(errors="replace").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.getenv("VM_HOST", "52.237.172.24"))
    ap.add_argument("--user", default=os.getenv("VM_USER", "azureuser"))
    ap.add_argument("--pass", dest="password", default=os.getenv("VM_PASS"))
    ap.add_argument("--swap-gb", type=int, default=2)
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

    # ---- 1) swap
    rc, out, _ = sh(c, "[ -f /swapfile ] && echo SI || echo NO")
    if out != "SI":
        print(f"creando swap de {args.swap_gb} GB…")
        rc, out, err = su(c, f"fallocate -l {args.swap_gb}G /swapfile && chmod 600 /swapfile && "
                             f"mkswap /swapfile >/dev/null && swapon /swapfile && echo SWAP_OK", pw, 600)
        print(out or err)
    else:
        rc, out, err = su(c, "swapon --show=NAME,SIZE --noheadings; swapon -a 2>/dev/null; echo (ya existía)", pw)
        print(out or err)
    rc, out, _ = sh(c, "grep -q '^/swapfile' /etc/fstab && echo EN_FSTAB || echo FALTA")
    if out == "FALTA":
        rc, out, err = su(c, "printf '/swapfile none swap sw 0 0\\n' >> /etc/fstab && "
                             "grep swapfile /etc/fstab", pw)
        print("fstab:", out or err)

    # ---- 2) journal limitado (los archivos se suben por SFTP: con printf se colaban los \n)
    sftp = c.open_sftp()
    with sftp.open(f"{REMOTE}/journald-limite-lab4.conf", "w") as fh:
        fh.write(JOURNALD)
    with sftp.open(f"{REMOTE}/99-lab4.conf", "w") as fh:
        fh.write(SYSCTL)
    sftp.close()
    rc, out, err = su(c, "mkdir -p /etc/systemd/journald.conf.d && "
                         f"cp {REMOTE}/journald-limite-lab4.conf /etc/systemd/journald.conf.d/limite-lab4.conf && "
                         "systemctl restart systemd-journald && "
                         "systemd-analyze cat-config systemd/journald.conf | grep -E 'SystemMaxUse|MaxRetentionSec'", pw)
    print("journald:", out or err)

    # ---- 3) swappiness
    rc, out, err = su(c, f"cp {REMOTE}/99-lab4.conf /etc/sysctl.d/99-lab4.conf && "
                         "sysctl --system 2>/dev/null | grep -i swappiness; sysctl vm.swappiness", pw)
    print("sysctl:", out or err)

    # ---- 4) comprobaciones de higiene
    print("\n=== comprobaciones ===")
    rc, out, err = sh(c, "ls /etc/logrotate.d/nginx >/dev/null 2>&1 && echo 'logrotate de nginx: OK' "
                         "|| echo 'logrotate de nginx: FALTA'; "
                         "grep -RhoiE 'Unattended-Upgrade::Automatic-Reboot \"[a-z]+\"' "
                         "/etc/apt/apt.conf.d/ 2>/dev/null | head -1 || echo 'automatic-reboot: no configurado (bien)'")
    print(out or err)

    rc, out, err = sh(c, "echo '--- swap ---'; free -m; echo; echo '--- disco ---'; df -h / | tail -1; "
                         "echo; echo '--- journal ---'; journalctl --disk-usage; "
                         "echo; echo '--- uptime/carga ---'; uptime")
    print(out or err)
    c.close()


if __name__ == "__main__":
    main()
