#!/usr/bin/env python3
"""
coap_client.py — Nodo constrained CoAP: envía las 3 variables como POST JSON al
gateway CoAP (UDP 5683, 127.0.0.1 en la VM).

Mide RTT request->response (datagrama UDP + confirmación CoAP) y tamaño de
payload; lo registra en evidencias/coap/client.jsonl.

Uso:
  python coap_client.py --duration 60 --interval 10 --log ../evidencias/coap/client.jsonl
"""

import argparse
import asyncio
import json
import os
import time

import aiocoap
from dotenv import load_dotenv

import common


async def main():
    ap = argparse.ArgumentParser(description="Cliente CoAP constrained")
    ap.add_argument("--gateway", default="127.0.0.1", help="IP del gateway CoAP")
    ap.add_argument("--port", type=int, default=5683)
    ap.add_argument("--duration", type=int, default=60)
    ap.add_argument("--interval", type=float, default=None)
    ap.add_argument("--log", default=None)
    args = ap.parse_args()

    load_dotenv()
    interval = float(args.interval or os.getenv("INTERVALO_SEGUNDOS", "10"))

    ctx = await aiocoap.Context.create_client_context()
    uri = f"coap://{args.gateway}:{args.port}/telemetry"

    logf = open(args.log, "a", encoding="utf-8") if args.log else None
    start = time.time()
    sent = 0
    rtts = []
    try:
        while True:
            if args.duration and time.time() - start >= args.duration:
                break
            payload, nbytes = common.payload_json()
            msg = aiocoap.Message(
                code=aiocoap.POST, payload=payload.encode("utf-8"), uri=uri
            )
            t0 = time.perf_counter()
            try:
                resp = await asyncio.wait_for(ctx.request(msg).response, timeout=10)
                rtt = (time.perf_counter() - t0) * 1000
                rtts.append(rtt)
                sent += 1
                rec = {
                    "t": common.ahora_iso(),
                    "proto": "coap",
                    "transport": "udp",
                    "bytes": nbytes,
                    "rtt_ms": round(rtt, 1),
                    "code": str(resp.code),
                    "seq": sent,
                }
                print(
                    f"[COAP] #{sent} {payload} ({nbytes} B, rtt {rtt:.1f} ms, {resp.code})"
                )
                if logf:
                    logf.write(json.dumps(rec) + "\n")
                    logf.flush()
            except asyncio.TimeoutError:
                print(f"[COAP] #{sent+1} TIMEOUT (datagrama perdido o gateway caído)")
            except aiocoap.error.NetworkError as e:
                print(f"[COAP] #{sent+1} NETWORK ERROR: {e} (gateway no responde)")
            await asyncio.sleep(interval)
    finally:
        await ctx.shutdown()
        if logf:
            logf.close()
        if rtts:
            n = len(rtts)
            print(
                f"[COAP] SUMMARY sent={n} rtt_avg={sum(rtts)/n:.1f}ms "
                f"min={min(rtts):.1f} max={max(rtts):.1f}"
            )


if __name__ == "__main__":
    asyncio.run(main())
