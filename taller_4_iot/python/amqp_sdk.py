#!/usr/bin/env python3
"""
amqp_sdk.py — Cliente AMQP 1.0 EXPLÍCITO hacia Azure IoT Central (device amqp-lab4-01).

Hallazgo clave del Lab 4: azure-iot-device (2.x) YA NO INCLUYE transporte AMQP
(v2.14.0 solo trae MQTT+HTTP; la eliminación de AMQP/uamqp ocurrió en las 2.x
tempranas). Por eso este cliente se construye a mano sobre uamqp — el mismo
espíritu "abrir la caja negra" del mqtt_explicito.py del Lab 3.

Qué hace:
  1. Descubre el hub vigente vía DPS (la app fue recreada; el hostname cambió).
  2. Construye el SAS token HMAC-SHA256 en memoria (misma fórmula que Lab 3,
     resource = {hub}/devices/{device_id}).
  3. Abre conexión AMQP 1.0 (TLS 5671), autentica por CBS (put-token al endpoint
     $cbs), abre el link de envío a devices/{id}/messages/events.
  4. Publica las 3 variables (Temperature, Humidity, Iluminance) midiendo
     latencia send -> disposition(accepted) del hub.

Uso:
  python amqp_sdk.py --duration 60 --interval 10 --log ../evidencias/amqp/run.jsonl
"""

import argparse
import json
import os
import time
from datetime import timedelta

import uamqp
from uamqp import SendClient, Message
from uamqp.authentication import SASTokenAuth
from dotenv import load_dotenv

import common
from common import build_sas_token


def main():
    ap = argparse.ArgumentParser(description="AMQP 1.0 explicit -> Azure IoT Central")
    ap.add_argument("--duration", type=int, default=60)
    ap.add_argument("--interval", type=float, default=None)
    ap.add_argument("--log", default=None)
    ap.add_argument("--debug", action="store_true", help="traza de frames AMQP")
    args = ap.parse_args()

    load_dotenv()
    device_id = os.getenv("AMQP_DEVICE_ID", "amqp-lab4-01")
    key = os.environ["AMQP_DEVICE_PRIMARY_KEY"]
    interval = float(args.interval or os.getenv("INTERVALO_SEGUNDOS", "10"))

    # 1) DPS: descubrir el hub vigente (la app fue recreada; idempotente)
    conn_str = common.central_conn_str(device_id, key)
    hub = conn_str.split("HostName=", 1)[1].split(";", 1)[0]
    resource = f"{hub}/devices/{device_id}"

    # 2) SAS token en memoria (HMAC-SHA256, Lab 3)
    token = build_sas_token(hub, device_id, key, ttl=86400)
    print(f"[AMQP] SAS token construido en memoria (se={token.split('&se=')[1].split('&')[0]}, "
          f"sr={resource})")

    # 3) Auth CBS + link de envío (target del endpoint D2C de IoT Hub)
    auth = SASTokenAuth(
        audience=resource,
        uri=f"amqps://{hub}",
        token=token,
        expires_in=timedelta(seconds=85000),
        timeout=15,
    )
    target = f"amqps://{hub}/devices/{device_id}/messages/events"
    t_c0 = time.perf_counter()
    client = SendClient(target, auth, debug=args.debug)
    # El handshake completo (TLS+CBS+attach) ocurre en el primer envío
    print(f"[AMQP] SendClient creado -> {target} (conn+auth al primer send)")

    logf = open(args.log, "a", encoding="utf-8") if args.log else None
    start = time.time()
    sent = 0
    failed = 0
    latencies = []
    try:
        while True:
            if args.duration and time.time() - start >= args.duration:
                break
            payload, nbytes = common.payload_json()
            t0 = time.perf_counter()
            client.queue_message(Message(body=payload.encode("utf-8")))
            result = client.send_all_messages(close_on_done=False)
            lat = (time.perf_counter() - t0) * 1000
            from uamqp.constants import MessageState
            ok = bool(result) and all(
                s in (MessageState.SendComplete, MessageState.ReceivedSettled)
                for s in result
            )
            sent += 1 if ok else 0
            failed += 0 if ok else 1
            latencies.append(lat)
            outcomes = [str(s) for s in result]
            rec = {
                "t": common.ahora_iso(),
                "proto": "amqp",
                "port": 5671,
                "transport": "tcp+tls",
                "bytes": nbytes,
                "payload": json.loads(payload),
                "latency_ms": round(lat, 1),
                "outcome": outcomes,
                "seq": sent,
            }
            print(
                f"[AMQP] #{sent} {payload} ({nbytes} B, "
                f"ack {lat:.1f} ms, {outcomes})"
            )
            if logf:
                logf.write(json.dumps(rec) + "\n")
                logf.flush()
            time.sleep(interval)
    finally:
        try:
            client.close()
        except Exception:
            pass
        if logf:
            logf.close()
        if latencies:
            n = len(latencies)
            print(
                f"[AMQP] SUMMARY sent={sent} failed={failed} "
                f"ack_avg={sum(latencies)/n:.1f}ms "
                f"min={min(latencies):.1f} max={max(latencies):.1f}"
            )


if __name__ == "__main__":
    main()
