#!/usr/bin/env python3
"""Ingestor Lab 5 — el puente MQTT -> InfluxDB (TSDB).

Se suscribe al topic lab5/telemetria y por cada mensaje:
  1. convierte el payload JSON a line protocol de InfluxDB v2,
  2. lo escribe en el bucket telemetria (precision ns, marca REAL del publicador),
  3. mide hop_ms: el salto broker->ingestor (tiempo que el mensaje tardo en
     salir del broker hacia nosotros, usando ts_ns del publicador),
  4. deja una linea JSONL de evidencia.

Por que existe esta pieza en lugar de la "Telegraf input MQTT" de Telegraf:
didactica y control — queremos MEDIR y registrar el salto por mensaje, y el
line protocol escrito a mano deja explicito el esquema (measurement
telemetria, 3 campos float) que despues se consulta con Flux en Grafana.
"""
import json
import os
import time

import paho.mqtt.client as mqtt
import requests

TOPIC = "lab5/telemetria"
FIELDS = ("Temperature", "Humidity", "Iluminance")


def to_line_protocol(d: dict) -> str:
    """measurement=telemetria, campos float, timestamp ns del publicador."""
    fields = ",".join(f"{k}={float(d[k])}" for k in FIELDS)
    return f"telemetria,device=lab5 {fields} {int(d['ts_ns'])}"


def main():
    host = os.environ.get("MQTT_HOST", "127.0.0.1")
    url = os.environ.get("INFLUX_URL", "http://127.0.0.1:8086")
    org = os.environ["INFLUX_ORG"]
    bucket = os.environ["INFLUX_BUCKET"]
    token = os.environ["INFLUX_TOKEN"]
    logf = os.environ.get("LIVE_JSONL", "evidencias/live-ingest.jsonl")
    os.makedirs(os.path.dirname(logf) or ".", exist_ok=True)

    write_url = f"{url}/api/v2/write?org={org}&bucket={bucket}&precision=ns"
    headers = {"Authorization": f"Bearer {token}",
               "Content-Type": "text/plain; charset=utf-8"}
    seq = 0

    def on_message(_c, _u, msg):
        nonlocal seq
        t_rx = time.time()
        d = json.loads(msg.payload.decode("utf-8"))
        hop_ms = round((t_rx - d["ts_ns"] / 1e9) * 1000, 1)  # ns -> s; mismo reloj VM
        status = None
        err = ""
        try:
            r = requests.post(write_url, headers=headers,
                              data=to_line_protocol(d), timeout=10)
            status = r.status_code
            if status != 204:
                err = r.text[:200]
        except Exception as e:  # influx caido: no matar la suscripcion
            err = str(e)[:200]
        seq += 1
        rec = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "seq": seq, "payload": d, "hop_ms": hop_ms,
               "influx_status": status, "error": err or None}
        with open(logf, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[INGEST] #{seq} hop {hop_ms} ms influx {status}"
              + (f" ERROR {err}" if err else ""), flush=True)

    client = mqtt.Client(client_id="lab5-ingest")
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    while True:
        try:
            client.connect(host, 1883, 30)
            break
        except Exception as e:
            print(f"[INGEST] esperando broker... {e}", flush=True)
            time.sleep(5)
    client.loop_start()  # mismo bug que el publicador: el loop de red debe
                         # ir en su hilo para recibir mensajes con el main dormido
    client.subscribe(TOPIC, qos=1)
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
