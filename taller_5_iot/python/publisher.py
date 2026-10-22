#!/usr/bin/env python3
"""Publicador Lab 5 — escenario "consola ambiental" en plataforma propia.

Genera las 3 variables del escenario (Temperature, Humidity, Iluminance) con
random-walk +-0.5 dentro de los rangos fisicos, IGUAL que taller_4_iot/python/
common.py (los 4 talleres comparten escenario para que todo sea comparable).

Cada lectura se publica por MQTT a mosquitto (topic lab5/telemetria, QoS 1)
y deja UNA linea JSONL de evidencia por mensaje (el "como viaja el mensaje"
que pide la rubrica didactica): seq, bytes, payload crudo y puback_ms, la
latencia real de confirmacion del broker medida en el cliente.

--caliente fuerza Temperature 33-38 C (fuera del rango fisico 16-32) para
DISPARAR la alerta de Grafana a demanda, tal como exige el laboratorio:
"forzar el valor desde el publicador y capturar el disparo".
"""
import argparse
import json
import os
import random
import time

import paho.mqtt.client as mqtt

LIMITS = {
    "Temperature": (16.0, 32.0),
    "Humidity": (35.0, 70.0),
    "Iluminance": (100.0, 800.0),
}
_state = {"Temperature": 24.0, "Humidity": 50.0, "Iluminance": 400.0}
TOPIC = "lab5/telemetria"


def generar_lectura(caliente: bool = False, state: dict | None = None) -> dict:
    """Random-walk +-0.5 respetando rangos; con caliente=True la temperatura
    salta a 33-38 C (umbral de la alerta) mientras dure el modo."""
    st = state if state is not None else _state
    for k, (lo, hi) in LIMITS.items():
        st[k] = round(min(hi, max(lo, st[k] + random.uniform(-0.5, 0.5))), 1)
    if caliente:
        st["Temperature"] = round(random.uniform(33.0, 38.0), 1)
    return dict(st)


def payload_json(lectura: dict) -> str:
    """JSON plano + marca de tiempo REAL en nanosegundos epoch (Influx usa ns;
    el ingestor la reutiliza para medir el salto broker->ingestor)."""
    d = dict(lectura)
    d["ts_ns"] = time.time_ns()
    return json.dumps(d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=60,
                    help="segundos entre mensajes (60 = corrida de 4 dias)")
    ap.add_argument("--duration", type=int, default=0,
                    help="0 = infinito; p.ej. 300 para una corrida corta")
    ap.add_argument("--caliente", action="store_true",
                    help="Temperature 33-38 C (forzar la alerta)")
    ap.add_argument("--client-suffix", default="",
                    help="sufijo del client_id si corres un 2do publicador")
    args = ap.parse_args()

    host = os.environ.get("MQTT_HOST", "127.0.0.1")
    logf = os.environ.get("LIVE_JSONL", "evidencias/live-publisher.jsonl")
    os.makedirs(os.path.dirname(logf) or ".", exist_ok=True)

    client = mqtt.Client(client_id="lab5-publisher" + args.client_suffix)
    # reconecta solo: si el broker reinicia, paho reintenta y la corrida sigue
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    while True:
        try:
            client.connect(host, 1883, 30)
            break
        except Exception as e:
            print(f"[MQTT] esperando broker... {e}", flush=True)
            time.sleep(5)
    client.loop_start()  # HILO DE RED: sin esto el PUBLISH QoS1 se encola y
                         # el PUBACK nunca llega (bug real de esta corrida:
                         # puback_ms=10005 y desconexiones por keepalive)

    t0, seq = time.time(), 0
    while args.duration == 0 or time.time() - t0 < args.duration:
        lec = generar_lectura(caliente=args.caliente)
        s = payload_json(lec)
        t_pub = time.monotonic()
        r = client.publish(TOPIC, s, qos=1)
        r.wait_for_publish(timeout=10)
        puback_ms = round((time.monotonic() - t_pub) * 1000, 1)
        seq += 1
        rec = {
            "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "seq": seq, "proto": "MQTT", "topic": TOPIC,
            "bytes": len(s.encode("utf-8")),
            "payload": json.loads(s), "puback_ms": puback_ms,
        }
        with open(logf, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[MQTT] #{seq} T={lec['Temperature']} H={lec['Humidity']} "
              f"L={lec['Iluminance']} puback {puback_ms} ms", flush=True)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
