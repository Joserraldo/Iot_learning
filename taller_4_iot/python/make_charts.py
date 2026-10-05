#!/usr/bin/env python3
"""
make_charts.py — Genera las gráficas de la comparativa MQTT · AMQP · CoAP (matplotlib).

Lee los .jsonl de evidencias/{mqtt,amqp,coap}/ y escribe PNG en evidencias/comparativa/.

Gráficas:
  1. barras_latencia_promedio.png  — latencia promedio ack por protocolo (local vs VM)
  2. boxplot_latencias.png         — dispersión de latencias por mensaje
  3. serie_temporal.png           — latencia por seq (muestra el handshake AMQP)
  4. diagrama_arquitectura.png     — arquitectura (3 devices, puertos, gateway, Central)
  5. bytes_por_mensaje.png         — bytes de payload por mensaje (60 B)

Uso:
  python python/make_charts.py
"""

import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

ROOT = Path(__file__).resolve().parent.parent
EVD = ROOT / "evidencias"
OUT = EVD / "comparativa"

LOCAL = {
    "mqtt": {"run": ["mqtt/run.jsonl"]},
    "amqp": {"run": ["amqp/run.jsonl"], "formula": "run.jsonl", "formal": "amqp/vm-formal.jsonl"},
    "coap": {"local": ["coap/vm-client-formal.jsonl"], "vm": ["coap/vm-client-formal.jsonl"]},
}

KEY = {"mqtt": "latency_ms", "amqp": "latency_ms", "coap": "rtt_ms"}


def load(proto, paths):
    rows = []
    for p in paths:
        f = EVD / p
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def lat(proto, rows):
    return [r[KEY[proto]] for r in rows]


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # local MQTT
    mqtt_local = load("mqtt", ["mqtt/run.jsonl"])
    amqp_local = load("amqp", ["amqp/run.jsonl"])
    coap_local = load("coap", ["coap/vm-client-formal.jsonl"])
    mqtt_vm = load("mqtt", ["mqtt/vm-formal.jsonl"])
    amqp_vm = load("amqp", ["amqp/vm-formal.jsonl"])
    coap_vm = load("coap", ["coap/vm-client-formal.jsonl"])

    # 1) Barras latencia promedio local vs VM (excluyendo el 1er msg de handshake)
    def avg(rows, key):
        vals = [r[key] for r in rows]
        return sum(vals) / len(vals) if vals else 0

    protos = ["MQTT", "AMQP", "CoAP"]
    local_avg = [
        avg(mqtt_local, "latency_ms"),
        avg([r for r in amqp_local if r["seq"] > 1], "latency_ms"),
        avg(coap_local, "rtt_ms"),
    ]
    vm_avg = [
        avg([r for r in mqtt_vm if r["seq"] > 1], "latency_ms"),
        avg([r for r in amqp_vm if r["seq"] > 1], "latency_ms"),
        avg(coap_vm, "rtt_ms"),
    ]

    import numpy as np

    x = np.arange(len(protos))
    w = 0.38
    fig, ax = plt.subplots(figsize=(8, 5))
    b1 = ax.bar(x - w / 2, local_avg, w, label="Local", color="#4C78A8")
    b2 = ax.bar(x + w / 2, vm_avg, w, label="VM (Azure)", color="#F58518")
    for bars in (b1, b2):
        for b in bars:
            ax.annotate(f"{b.get_height():.0f} ms", (b.get_x() + b.get_width() / 2, b.get_height()),
                       ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x, protos)
    ax.set_ylabel("Latencia de confirmación (ms)")
    ax.set_title("Latencia promedio de ack por protocolo — local vs VM (n≥4 msgs, sin handshake)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "barras_latencia_promedio.png", dpi=150)
    plt.close(fig)

    # 2) Box/strip dispersión por mensaje (VM formal, todos los mensajes)
    fig, ax = plt.subplots(figsize=(8, 5))
    data = [
        [r["latency_ms"] for r in mqtt_vm],
        [r["latency_ms"] for r in amqp_vm],
        [r["rtt_ms"] for r in coap_vm],
    ]
    bp = ax.boxplot(data, tick_labels=protos, patch_artist=True, widths=0.45)
    colors = ["#4C78A8", "#F58518", "#54A24B"]
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.5)
    for i, vals in enumerate(data, start=1):
        jitter = np.random.uniform(-0.12, 0.12, size=len(vals))
        ax.scatter(np.full(len(vals), i) + jitter, vals, s=35, color="#333333", alpha=0.7,
                   edgecolors="white", linewidths=0.6, zorder=3)
    ax.set_ylabel("Latencia (ms)")
    ax.set_title("Dispersión de latencia por mensaje (VM, corridas formales 90 s)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "boxplot_latencias.png", dpi=150)
    plt.close(fig)

    # 3) Serie temporal: latencia por seq, una corrida de cada protocolo (VM formal)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot([r["seq"] for r in mqtt_vm], [r["latency_ms"] for r in mqtt_vm],
            "o-", color="#4C78A8", label="MQTT", markersize=5)
    ax.plot([r["seq"] for r in amqp_vm], [r["latency_ms"] for r in amqp_vm],
            "s-", color="#F58518", label="AMQP (1er msg = handshake)", markersize=5)
    ax.plot([r["seq"] for r in coap_vm], [r["rtt_ms"] for r in coap_vm],
            "^-", color="#54A24B", label="CoAP (RTT cliente)", markersize=5)
    ax.axvline(1, color="gray", linestyle=":", linewidth=0.8)
    ax.text(1.15, 430, "AMQP: primer mensaje = handshake TLS+CBS+attach", fontsize=9, color="#F58518")
    ax.set_xlabel("Número de mensaje (seq)")
    ax.set_ylabel("Latencia (ms)")
    ax.set_title("Serie temporal de latencia por mensaje (VM, corridas formales)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "serie_temporal.png", dpi=150)
    plt.close(fig)

    # 5) Bytes por mensaje (payload 60 B en los 3)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bytes_v = [60, 60, 60]
    ax.bar(protos, bytes_v, color=["#4C78A8", "#F58518", "#54A24B"])
    for i, v in enumerate(bytes_v):
        ax.annotate(f"{v} B", (i, v), ha="center", va="bottom", fontsize=10)
    ax.set_ylabel("Bytes de payload")
    ax.set_title("Tamaño de payload por mensaje (idéntico en los 3 protocolos)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "bytes_por_mensaje.png", dpi=150)
    plt.close(fig)

    # 4) Diagrama de arquitectura
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    def box(x, y, w, h, text, fc="white", ec="black"):
        ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                                             fc=fc, ec=ec, linewidth=1.2))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9, wrap=True)

    box(0.3, 4.2, 2.2, 1.0, "Cliente MQTT\nmqtt-baseline-01\n(paho, TLS 8883)", "#D6E4F0")
    box(0.3, 2.6, 2.2, 1.0, "Cliente AMQP 1.0\namqp-lab4-01\nuamqp, TLS 5671", "#FDE8D2")
    box(0.3, 1.0, 2.2, 1.0, "Nodo CoAP\ncoap-client\nUDP 5683", "#D8EBD1")

    box(3.3, 2.0, 3.2, 1.4, "Gateway CoAP (VM)\nservidor UDP 5683 +\npuente MQTT TLS 8883\n(coap-gateway-01)", "#F4D35E")
    ax.annotate("POST /telemetry\n(CoAP CON → 2.04)", (2.5, 1.5), (2.9, 2.1),
                arrowprops=dict(arrowstyle="->", color="#54A24B"), fontsize=8,
                color="#54A24B", ha="center")

    box(7.2, 3.2, 2.4, 1.6, "Azure IoT Central\nclima-salones-app-jose\n(hub iotc-…-azure-devices.net)", "#D7D9F0")

    ax.annotate("", (2.5, 4.7), (7.2, 4.4), arrowprops=dict(arrowstyle="->", color="#4C78A8"))
    ax.text(4.8, 5.0, "MQTT publish QoS1 → PUBACK", fontsize=8, color="#4C78A8")
    ax.annotate("", (2.5, 3.1), (7.2, 3.6), arrowprops=dict(arrowstyle="->", color="#F58518"))
    ax.text(4.8, 3.85, "AMQP 1.0 → disposition", fontsize=8, color="#F58518")
    ax.annotate("", (6.5, 2.7), (7.2, 2.9), arrowprops=dict(arrowstyle="->", color="#F58518"))
    ax.text(6.8, 3.1, "MQTT puente", fontsize=8, color="#F58518")

    ax.annotate("", (3.3, 3.5), (0.3, 4.7), arrowprops=dict(arrowstyle="->", color="#888888"))
    ax.annotate("", (3.3, 3.5), (0.3, 3.1), arrowprops=dict(arrowstyle="->", color="#888888"))
    ax.annotate("", (3.3, 3.5), (0.3, 1.7), arrowprops=dict(arrowstyle="->", color="#888888"))
    ax.text(1.6, 4.0, "mismo payload\n60 B", fontsize=8, ha="center", color="#555555")

    ax.annotate("", (7.2, 2.6), (3.3, 2.4), arrowprops=dict(arrowstyle="->", color="#888888"))
    ax.text(5.3, 2.35, "reconexión automática SDK", fontsize=8, color="#555555")

    ax.text(5, 5.6, "Arquitectura del Lab 4 — 3 protocolos hacia IoT Central", fontsize=12,
            ha="center", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "diagrama_arquitectura.png", dpi=150)
    plt.close(fig)

    print("Gráficas generadas en:", OUT)
    for f in sorted(OUT.iterdir()):
        print(" -", f.name)


if __name__ == "__main__":
    main()
