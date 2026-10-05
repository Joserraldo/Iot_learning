#!/usr/bin/env python3
"""
mqtt_baseline.py — Línea base MQTT del Lab 4: cliente MQTT explícito (paho-mqtt,
sin SDK) adaptado del mqtt_explicito.py del Lab 3.

La app fue recreada, así que este run re-registra por DPS (descubre el hub
vigente) con el device dedicado mqtt-baseline-01. Publica las mismas 3 variables
y mide latencia publish -> PUBACK (QoS 1), igual que el Lab 3, para que la
comparación MQTT · AMQP · CoAP sea equivalente.

Uso:
  python mqtt_baseline.py --duration 60 --interval 10 --log ../evidencias/mqtt/run.jsonl
"""

import argparse
import json
import os
import ssl
import time

import paho.mqtt.client as pmqtt
from dotenv import load_dotenv

import common

STATE = {"connected": False}


def on_connect(client, userdata, flags, rc):
    STATE["connected"] = rc == 0
    print(f"[MQTT] conectado (rc={rc})")


def main():
    ap = argparse.ArgumentParser(description="MQTT baseline -> Azure IoT Central")
    ap.add_argument("--duration", type=int, default=60)
    ap.add_argument("--interval", type=float, default=None)
    ap.add_argument("--log", default=None)
    args = ap.parse_args()

    load_dotenv()
    device_id = os.getenv("MQTT_DEVICE_ID", "mqtt-baseline-01")
    key = os.environ["MQTT_DEVICE_PRIMARY_KEY"]
    interval = float(args.interval or os.getenv("INTERVALO_SEGUNDOS", "10"))

    # DPS: descubrir el hub vigente (la app fue recreada)
    conn_str = common.central_conn_str(device_id, key)
    hub = conn_str.split("HostName=", 1)[1].split(";", 1)[0]

    sas = common.build_sas_token(hub, device_id, key, ttl=86400)
    username = f"{hub}/{device_id}/?api-version=2021-04-12"
    topic = f"devices/{device_id}/messages/events/"

    # paho 1.6 (azure-iot-device fija paho<2.0) — API callbacks v1
    c = pmqtt.Client(client_id=device_id, protocol=pmqtt.MQTTv311)
    c.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    c.username_pw_set(username, password=sas)
    c.on_connect = on_connect
    c.connect(hub, 8883, keepalive=30)
    c.loop_start()

    logf = open(args.log, "a", encoding="utf-8") if args.log else None
    sent = 0
    latencies = []
    start = time.time()
    try:
        while True:
            if args.duration and time.time() - start >= args.duration:
                break
            if not STATE["connected"]:
                time.sleep(0.5)
                continue
            payload, nbytes = common.payload_json()
            info = c.publish(topic, payload, qos=1)
            t0 = time.perf_counter()
            while not info.is_published() and time.perf_counter() - t0 < 10:
                time.sleep(0.001)
            lat = (time.perf_counter() - t0) * 1000
            sent += 1
            latencies.append(lat)
            rec = {
                "t": common.ahora_iso(),
                "proto": "mqtt",
                "port": 8883,
                "transport": "tcp+tls",
                "bytes": nbytes,
                "payload": json.loads(payload),
                "latency_ms": round(lat, 1),
                "topic": topic,
                "seq": sent,
            }
            print(f"[MQTT] #{sent} {payload} ({nbytes} B, puback {lat:.1f} ms)")
            if logf:
                logf.write(json.dumps(rec) + "\n")
                logf.flush()
            time.sleep(interval)
    finally:
        c.loop_stop()
        c.disconnect()
        if logf:
            logf.close()
        if latencies:
            n = len(latencies)
            print(
                f"[MQTT] SUMMARY sent={n} "
                f"puback_avg={sum(latencies)/n:.1f}ms "
                f"min={min(latencies):.1f} max={max(latencies):.1f}"
            )


if __name__ == "__main__":
    main()
