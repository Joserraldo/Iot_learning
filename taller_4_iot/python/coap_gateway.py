#!/usr/bin/env python3
"""
coap_gateway.py — Gateway propio: servidor CoAP (UDP 5683) + puente a Azure IoT Central.

CoAP no es nativo de IoT Central: este gateway es el componente intermedio que
recibe los datagramas del nodo constrained (coap_client.py) y reenvía la
telemetría a Central con el device dedicado coap-gateway-01 (transporte MQTT del
SDK). Registra en evidencias/coap/: bytes recibidos, RTT CoAP y latencia de
forwarding hacia Central.

Uso:
  python coap_gateway.py --log ../evidencias/coap/gateway.jsonl
"""

import argparse
import asyncio
import json
import os
import time

import aiocoap
import aiocoap.resource as resource
from dotenv import load_dotenv

from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import Message

import common


class TelemetryResource(resource.Resource):
    """POST /telemetry — recibe JSON de 3 variables y lo reenvía a Central."""

    def __init__(self, central_client, logf):
        super().__init__()
        self.central = central_client
        self.logf = logf
        self.seq = 0

    async def render_post(self, request):
        payload = request.payload
        nbytes = len(payload)
        t0 = time.perf_counter()
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return aiocoap.Message(code=aiocoap.BAD_REQUEST, payload=b"bad json")

        # validar 3 variables
        missing = [k for k in LIMITS_KEYS if k not in data]
        if missing:
            return aiocoap.Message(
                code=aiocoap.BAD_REQUEST, payload=f"missing {missing}".encode()
            )

        await self.central.send_message(Message(payload))
        fw_ms = (time.perf_counter() - t0) * 1000
        self.seq += 1
        rec = {
            "t": common.ahora_iso(),
            "proto": "coap",
            "coap_port": 5683,
            "transport": "udp",
            "bytes": nbytes,
            "payload": data,
            "forward_latency_ms": round(fw_ms, 1),
            "seq": self.seq,
        }
        print(f"[GW] #{self.seq} recibido {nbytes} B -> Central ack {fw_ms:.1f} ms")
        if self.logf:
            self.logf.write(json.dumps(rec) + "\n")
            self.logf.flush()
        return aiocoap.Message(code=aiocoap.CHANGED, payload=b"ok")


LIMITS_KEYS = list(common.LIMITS.keys())


async def main():
    ap = argparse.ArgumentParser(description="Gateway CoAP -> IoT Central")
    ap.add_argument("--bind", default="127.0.0.1", help="bind del servidor CoAP")
    ap.add_argument("--port", type=int, default=5683)
    ap.add_argument("--log", default=None)
    args = ap.parse_args()

    load_dotenv()
    device_id = os.getenv("COAP_DEVICE_ID", "coap-gateway-01")
    key = os.environ["COAP_DEVICE_PRIMARY_KEY"]

    # DPS: la app fue recreada — descubrir el hub vigente (idempotente)
    conn_str = await asyncio.to_thread(common.central_conn_str, device_id, key)

    central = IoTHubDeviceClient.create_from_connection_string(conn_str)
    print(f"[GW] puente {device_id} conectando…")
    t0 = time.perf_counter()
    await central.connect()
    print(f"[GW] puente conectado en {(time.perf_counter()-t0)*1000:.0f} ms")

    logf = open(args.log, "a", encoding="utf-8") if args.log else None

    root = resource.Site()
    root.add_resource(["telemetry"], TelemetryResource(central, logf))
    ctx = await aiocoap.Context.create_server_context(root, bind=(args.bind, args.port))
    print(f"[GW] servidor CoAP escuchando udp://{args.bind}:{args.port}/telemetry")

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await ctx.shutdown()
        await central.shutdown()
        if logf:
            logf.close()
        print("[GW] fin")


if __name__ == "__main__":
    asyncio.run(main())
