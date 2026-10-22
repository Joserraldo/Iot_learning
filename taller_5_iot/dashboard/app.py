#!/usr/bin/env python3
"""Pagina didactica Lab 5 — "como viaja un mensaje" en la plataforma propia.

Lee (solo lectura) los JSONL de evidencia que dejan publisher.py e ingest.py
en ~/taller_5_iot/evidencias/ y muestra, en vivo:
  - la cadena publicador -> mosquitto -> ingestor -> InfluxDB -> Grafana,
  - la linea cruda por mensaje ([MQTT] #123 ... puback 8.4 ms), que es la
    evidencia didactica que pide el laboratorio,
  - los aggregates (msgs totales, puback medio, hop medio, influx OK).

Rutas SIN prefijo: nginx la frontea en /taller5/ y el HTML usa URLs
relativas, asi funciona detras del subpath sin tocar codigo.
"""
import json
import os

from flask import Flask, jsonify, render_template

app = Flask(__name__)
EV = os.environ.get("EVIDENCIAS",
                    "/home/azureuser/taller_5_iot/evidencias")
GRAFANA_URL = os.environ.get(
    "GRAFANA_URL",
    "https://iotcentraljose.duckdns.org/taller5/grafana/d/lab5")


def tail_jsonl(path, n=40):
    """Ultimas n lineas, leyendo solo el final del archivo (no O(todo) por
    refresco — leccion del taller 4 con los logs de dias)."""
    if not os.path.exists(path):
        return [], 0
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        f.seek(max(0, size - 400_000))
        lines = f.read().decode("utf-8", "replace").splitlines()
    total = len(lines)
    if size > 400_000:  # el tail no es todo: contar barato con wc-like
        total = sum(1 for _ in open(path, "rb"))
    return [json.loads(l) for l in lines[-n:] if l.strip()], total


@app.get("/api/estado")
def estado():
    pub, n_pub = tail_jsonl(f"{EV}/live-publisher.jsonl")
    ing, n_ing = tail_jsonl(f"{EV}/live-ingest.jsonl")
    def avg(xs):
        xs = [x for x in xs if x is not None]
        return round(sum(xs) / len(xs), 1) if xs else None
    return jsonify(
        publisher=pub, ingest=ing,
        publicados=n_pub, ingeridos=n_ing,
        puback_ms_avg=avg([p.get("puback_ms") for p in pub]),
        hop_ms_avg=avg([i.get("hop_ms") for i in ing]),
        influx_ok=sum(1 for i in ing if i.get("influx_status") == 204),
        grafana_url=GRAFANA_URL,
    )


@app.get("/")
def index():
    return render_template("index.html", grafana_url=GRAFANA_URL)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8090)
