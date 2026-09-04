#!/usr/bin/env python
"""Transfiere un archivo local a la VM por SSH usando base64 (robusto con rutas especiales).
Uso: python vm_push.py <local_path> <remote_path>
"""
import os
import sys
import base64
import paramiko

host = os.environ.get("VM_HOST", "")
user = os.environ.get("VM_USER", "")
password = os.environ.get("VM_PASS", "")

if not (host and user and password):
    sys.stderr.write("ERROR: faltan VM_HOST/VM_USER/VM_PASS\n")
    sys.exit(2)

local = sys.argv[1]
remote = sys.argv[2]

with open(local, "rb") as f:
    data = base64.b64encode(f.read()).decode("ascii")

# Dividir en bloques para evitar límites de longitud de comando
chunks = [data[i:i+1000] for i in range(0, len(data), 1000)]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=25)

# Crear archivo temporal en /tmp con todos los bloques
build_cmd = "cat > /tmp/push.b64 << 'ENDOFBASE64'\n" + "\n".join(chunks) + "\nENDOFBASE64\n"
stdin, stdout, stderr = client.exec_command(build_cmd, timeout=60)
stdout.read()
client.exec_command(f"base64 -d /tmp/push.b64 > '{remote}' && rm /tmp/push.b64 && echo push-ok")[1].read()
client.close()
print(f"OK: {remote} ({len(data)} b64 chars)")