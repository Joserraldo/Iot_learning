#!/usr/bin/env python
"""Tunel SSH local->VM con paramiko (sin pedir password interactivo).
Expone un puerto local apuntando a un puerto de la VM.

Credenciales: de variables de entorno VM_HOST/VM_USER/VM_PASS, o de un archivo
pasado con --creds (lineas clave=valor). El archivo NUNCA debe estar en el repo.

Uso:
  python tools/vm_tunnel.py --creds <ruta> --local 5000 --remote 5000
  # luego abre http://localhost:5000
"""
import os
import sys
import socket
import select
import threading
import argparse

import paramiko


def load_creds(path):
    if path and os.path.exists(path):
        d = {}
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip()
        return d
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--creds", default="")
    ap.add_argument("--local", type=int, default=5000)
    ap.add_argument("--remote", type=int, default=5000)
    ap.add_argument("--remote-host", default="localhost")
    args = ap.parse_args()

    creds = load_creds(args.creds)
    host = creds.get("VM_HOST") or os.environ.get("VM_HOST", "")
    user = creds.get("VM_USER") or os.environ.get("VM_USER", "")
    pw = creds.get("VM_PASS") or os.environ.get("VM_PASS", "")
    if not (host and user and pw):
        sys.stderr.write("ERROR: faltan VM_HOST/VM_USER/VM_PASS\n")
        sys.exit(2)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=pw, timeout=25)
    transport = client.get_transport()
    transport.set_keepalive(20)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", args.local))
    srv.listen(16)
    print(f"[tunnel] http://localhost:{args.local} -> {host}:{args.remote} ({args.remote_host})", flush=True)

    def pump(src, dst):
        try:
            while True:
                data = src.recv(4096)
                if not data:
                    break
                dst.sendall(data)
        except Exception:
            pass
        finally:
            try:
                dst.shutdown(socket.SHUT_WR)
            except Exception:
                pass

    while True:
        sock, addr = srv.accept()
        try:
            chan = transport.open_channel(
                "direct-tcpip", (args.remote_host, args.remote), addr)
        except Exception as e:
            print(f"[tunnel] open_channel fail: {e}", flush=True)
            sock.close()
            continue
        threading.Thread(target=pump, args=(sock, chan), daemon=True).start()
        threading.Thread(target=pump, args=(chan, sock), daemon=True).start()


if __name__ == "__main__":
    main()
