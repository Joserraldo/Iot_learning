#!/usr/bin/env python
"""Helper SSH para subir archivos a la VM via SFTP.
Lee credenciales SOLO de variables de entorno.
Uso: python vm_upload.py <local_path> <remote_path>
"""
import os
import sys
import paramiko

host = os.environ.get("VM_HOST", "")
user = os.environ.get("VM_USER", "")
password = os.environ.get("VM_PASS", "")

if not (host and user and password):
    sys.stderr.write("ERROR: faltan VM_HOST/VM_USER/VM_PASS\n")
    sys.exit(2)

local = sys.argv[1]
remote = sys.argv[2]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=25)
sftp = client.open_sftp()
sftp.put(local, remote)
sftp.close()
client.close()
print(f"OK: {local} -> {remote}")