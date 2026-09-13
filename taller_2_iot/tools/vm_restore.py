#!/usr/bin/env python
"""One-shot: verificar/restaurar la operacion de la VM tras un Reset password.

Hace en secuencia lo de la guia (pasos 3, 4 y 5) y reporta con codigos de salida:
  0 = VM operativa (nodo corriendo + 'Conectado a IoT Central' + /api/estado 200)
  2 = faltan VM_HOST/VM_USER/VM_PASS
  3 = autenticacion SSH rechazada (el reset aun no aplica o VM_PASS es otra)
  4 = SSH OK pero el nodo/log no confirman conexion a IoT Central
  5 = nodo OK pero el dashboard (localhost:5000/api/estado via tunel) no responde 200

Lee credenciales SOLO de variables de entorno (nunca de archivos), igual que
vm_ssh.py / vm_push.py / vm_tunnel.py.

Uso:
  python tools/vm_restore.py --dry-run   # muestra el plan sin tocar la red
  python tools/vm_restore.py             # ejecuta la verificacion completa
"""
import os
import re
import sys
import time

import paramiko

HOST = os.environ.get("VM_HOST", "")
USER = os.environ.get("VM_USER", "")
PASSWORD = os.environ.get("VM_PASS", "")
DRY = "--dry-run" in sys.argv

PLAN = [
    "1. SSH login (hostname && uptime)",
    "2. pgrep -af python-vm-01.py; si NO-CORRE -> bash ~/taller_iot/start.sh",
    "3. tail -n 25 ~/taller_iot/run.log  (buscar 'Conectado a IoT Central')",
    "4. tunel direct-tcpip -> GET http://localhost:5000/api/estado (esperar 200)",
]


def die(code, msg):
    sys.stderr.write(msg.rstrip() + "\n")
    sys.exit(code)


def main():
    if not (HOST and USER and (PASSWORD or DRY)):
        die(2, "ERROR: faltan VM_HOST/VM_USER/VM_PASS (exportar en la sesion, ver guia paso 2)")

    if DRY:
        print(f"[dry-run] destino: {USER}@{HOST}")
        for p in PLAN:
            print(f"[dry-run] {p}")
        print("[dry-run] OK: credenciales presentes; no se toco la red.")
        return 0

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOST, username=USER, password=PASSWORD, timeout=25)
    except paramiko.AuthenticationException:
        die(3, "AUTH_FALLADA: la VM sigue rechazando esa credencial "
               "(revisa que el Reset password del Portal se completo, con 'Restart required' si aplica)")
    except Exception as exc:  # timeout/no-route etc.
        die(3, f"CONEXION_FALLADA: {exc!r} (VM apagada/Starting o NSG bloqueando TCP/22?)")

    def run(cmd, t=60):
        stdin, stdout, stderr = client.exec_command(cmd, timeout=t)
        return stdout.read().decode("utf-8", "replace") + stderr.read().decode("utf-8", "replace")

    # 1. identidad
    ident = run("hostname && uptime").strip()
    print("--- 1. identidad ---\n" + ident)

    # 2. nodo corriendo o arrancarlo
    procs = run("pgrep -af python-vm-01.py || echo NO-CORRE").strip()
    print("--- 2. procesos ---\n" + procs)
    if "NO-CORRE" in procs:
        print("--- arrancando con start.sh ---")
        print(run("bash ~/taller_iot/start.sh").strip())
        time.sleep(8)  # dar tiempo al venv + arranque del TLS contra IoT Central
        procs = run("pgrep -af python-vm-01.py || echo NO-CORRE").strip()
        print("--- 2b. procesos tras arranque ---\n" + procs)
        if "NO-CORRE" in procs:
            die(4, "NODO_NO_ARRANCA: revisa 'tail -n 50 ~/taller_iot/run.log' en la VM")

    # 3. log: buscar marca de conexion (con un reintento a los 10 s)
    log = run("tail -n 25 ~/taller_iot/run.log")
    if not re.search(r"Conectado a IoT Central", log):
        time.sleep(10)
        log = run("tail -n 25 ~/taller_iot/run.log")
    print("--- 3. run.log (ultimas lineas) ---\n" + log.rstrip())
    if not re.search(r"Conectado a IoT Central", log):
        die(4, "LOG_SIN_CONEXION: el nodo corre pero no confirmo 'Conectado a IoT Central' "
               "(¿cert IoT Central vencida? ¿device key?). Revisar run.log completo.")

    # 4. dashboard via tunel SSH interno (direct-tcpip sobre la misma conexion)
    chan = None
    try:
        import http.client
        chan = client.get_transport().open_channel(
            "direct-tcpip", ("localhost", 5000), ("127.0.0.1", 0), timeout=10)
        conn = http.client.HTTPConnection("localhost", 5000, timeout=10)
        conn.request("GET", "/api/estado")
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", "replace")[:200]
        print(f"--- 4. GET /api/estado -> {resp.status} ---\n{body}")
        if resp.status != 200:
            die(5, f"DASHBOARD_BAD_STATUS: {resp.status}")
    except SystemExit:
        raise
    except Exception as exc:
        die(5, f"DASHBOARD_NO_RESPONDE: {exc!r} (¿Flask murio? ver run.log)")
    finally:
        if chan:
            chan.close()

    print("RESUMEN: VM OPERATIVA ✔ (auth OK, nodo corriendo, IoT Central conectado, API 200)")
    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
