#!/usr/bin/env python
"""Helper SSH para operar la VM de Laboratorio 2.
Lee credenciales SOLO de variables de entorno (nunca de archivos).
Uso: python vm_ssh.py "<comando_bash>"
"""
import os
import sys
import paramiko

host = os.environ.get("VM_HOST", "")
user = os.environ.get("VM_USER", "")
password = os.environ.get("VM_PASS", "")
command = sys.argv[1] if len(sys.argv) > 1 else "echo no-command"

if not (host and user and password):
    sys.stderr.write("ERROR: faltan VM_HOST/VM_USER/VM_PASS\n")
    sys.exit(2)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=25)
stdin, stdout, stderr = client.exec_command(command, timeout=120)
out = stdout.read().decode("utf-8", "replace")
err = stderr.read().decode("utf-8", "replace")
print(out, end="")
if err.strip():
    print("[stderr]", err, end="")
client.close()
