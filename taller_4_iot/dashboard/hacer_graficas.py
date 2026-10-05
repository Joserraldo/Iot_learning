#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hacer_graficas.py — genera los PNG de una captura de evidencia (matplotlib/Agg).

Uso:  .venv/bin/python dashboard/hacer_graficas.py evidencias/capturas/captura-YYYYMMDD-HHMMSS

Produce en esa carpeta: barras_latencia.png, serie_temporal.png,
boxplot_latencias.png, bytes_por_mensaje.png
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR = {"mqtt": "#38bdf8", "amqp": "#a78bfa", "coap": "#34d399"}
TITULO = {"mqtt": "MQTT (8883)", "amqp": "AMQP (5671)", "coap": "CoAP (5683/udp)"}
FONDO = "#0b1220"
TEXTO = "#e2e8f0"


def leer(path: Path, clave: str):
    ts, vs = [], []
    if not path.exists():
        return ts, vs
    for linea in path.read_text(errors="replace").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            r = json.loads(linea)
        except json.JSONDecodeError:
            continue
        v = r.get(clave)
        if isinstance(v, (int, float)):
            ts.append(r.get("t", "")[11:19])
            vs.append(v)
    return ts, vs


def estilo(ax):
    ax.set_facecolor(FONDO)
    ax.grid(True, color="#1e293b", lw=0.8)
    ax.tick_params(colors=TEXTO, labelsize=9)
    for s in ax.spines.values():
        s.set_color("#1e293b")
    ax.xaxis.label.set_color(TEXTO)
    ax.yaxis.label.set_color(TEXTO)
    ax.title.set_color(TEXTO)


def figura(w=9, h=4.6):
    fig, ax = plt.subplots(figsize=(w, h), dpi=150)
    fig.patch.set_facecolor(FONDO)
    estilo(ax)
    return fig, ax


def main():
    carpeta = Path(sys.argv[1]).resolve()
    datos = {
        "mqtt": leer(carpeta / "mqtt.jsonl", "latency_ms"),
        "amqp": leer(carpeta / "amqp.jsonl", "latency_ms"),
        "coap": leer(carpeta / "coap.jsonl", "rtt_ms"),
    }
    gw = leer(carpeta / "coap-gateway.jsonl", "forward_latency_ms")

    # 1) barras de latencia promedio
    fig, ax = figura()
    nombres, promedios, colores = [], [], []
    for p in ("mqtt", "amqp", "coap"):
        vals = datos[p][1]
        if not vals:
            continue
        nombres.append(TITULO[p])
        promedios.append(sum(vals) / len(vals))
        colores.append(COLOR[p])
    barras = ax.bar(nombres, promedios, color=colores, width=0.55)
    ax.bar_label(barras, fmt="%.1f ms", color="#0b1220", fontsize=11, fontweight="bold",
                 label_type="center")
    amqp = datos["amqp"][1]
    if len(amqp) > 1:
        steady = sum(amqp[1:]) / len(amqp[1:])
        ax.axhline(steady, color=COLOR["amqp"], ls="--", lw=1,
                   label=f"AMQP steady (sin handshake) {steady:.1f} ms")
        ax.legend(facecolor=FONDO, edgecolor="#1e293b", labelcolor=TEXTO, fontsize=9)
    ax.set_ylabel("latencia promedio (ms)")
    ax.set_title("Latencia promedio por protocolo — medición en la VM (52.237.172.24)")
    ax.set_ylim(0, max(promedios) * 1.35 if promedios else 1)
    fig.tight_layout()
    fig.savefig(carpeta / "barras_latencia.png", facecolor=FONDO)
    plt.close(fig)

    # 2) series temporales superpuestas
    fig, ax = figura(h=4.2)
    for p in ("mqtt", "amqp", "coap"):
        ts, vs = datos[p]
        if vs:
            ax.plot(range(len(vs)), vs, marker="o", ms=3.5, lw=1.6,
                    color=COLOR[p], label=TITULO[p])
    if gw[1]:
        ax.plot(range(len(gw[1])), gw[1], lw=1.2, ls=":", color="#f472b6",
                label="CoAP gateway → Central (forwarding)")
    ax.set_xlabel("muestra (#)")
    ax.set_ylabel("latencia (ms)")
    ax.set_title("Latencia por muestra — las 3 series sobre la misma escala")
    ax.legend(facecolor=FONDO, edgecolor="#1e293b", labelcolor=TEXTO, fontsize=9)
    fig.tight_layout()
    fig.savefig(carpeta / "serie_temporal.png", facecolor=FONDO)
    plt.close(fig)

    # 3) boxplot de distribución (se excluye el 1er mensaje AMQP: es el handshake
    #    TLS+CBS+attach y su ~500 ms aplastaba la escala de todos los demás)
    fig, ax = figura(h=4.4)
    series, etiquetas, usados = [], [], []
    for p in ("mqtt", "amqp", "coap"):
        vs = datos[p][1]
        if not vs:
            continue
        if p == "amqp" and len(vs) > 1:
            vs = vs[1:]
        series.append(vs)
        etiquetas.append(TITULO[p])
        usados.append(p)
    if series:
        est = dict(patch_artist=True, widths=0.5,
                   medianprops=dict(color="#ffffff", lw=2.2),
                   whiskerprops=dict(color="#94a3b8", lw=1.3),
                   capprops=dict(color="#94a3b8", lw=1.3),
                   flierprops=dict(marker="o", markerfacecolor="#f8fafc",
                                   markeredgecolor="none", markersize=4, alpha=.85))
        try:                                   # matplotlib >= 3.9
            bp = ax.boxplot(series, tick_labels=etiquetas, **est)
        except TypeError:                      # matplotlib < 3.9
            bp = ax.boxplot(series, labels=etiquetas, **est)
        for caja, p in zip(bp["boxes"], usados):
            caja.set_facecolor(COLOR[p])
            caja.set_edgecolor("#e2e8f0")
            caja.set_linewidth(1.4)
            caja.set_alpha(0.55)
        for i, vs in enumerate(series, start=1):
            ax.scatter([i + ((j % 7) - 3) * 0.04 for j in range(len(vs))], vs,
                       color="#f8fafc", s=7, alpha=0.35, zorder=1.5)
        todos = [v for s in series for v in s]
        lo, hi = min(todos), max(todos)
        rango = max(hi - lo, 2.0)
        ax.set_ylim(lo - rango * 0.18, hi + rango * 0.18)
        ax.set_title("Distribución de latencias por protocolo (AMQP sin el 1er mensaje de handshake)")
        ax.set_ylabel("latencia (ms)")
    fig.tight_layout()
    fig.savefig(carpeta / "boxplot_latencias.png", facecolor=FONDO)
    plt.close(fig)

    # 4) bytes por mensaje
    fig, ax = figura(w=7, h=3.8)
    nombres, bytes_msg = [], []
    for p in ("mqtt", "amqp", "coap"):
        if datos[p][1]:
            nombres.append(TITULO[p])
            bytes_msg.append(60)
    if nombres:
        barras = ax.bar(nombres, bytes_msg, color=[COLOR[p] for p in ("mqtt", "amqp", "coap")
                                                   if datos[p][1]], width=0.5)
        ax.bar_label(barras, fmt="%d B", color=TEXTO, fontsize=10, padding=3)
    ax.set_ylim(0, 80)
    ax.set_ylabel("payload (bytes)")
    ax.set_title("Payload idéntico de las 3 variables (60 B) — el overhead va en la cabecera")
    fig.tight_layout()
    fig.savefig(carpeta / "bytes_por_mensaje.png", facecolor=FONDO)
    plt.close(fig)

    print("graficas OK:", sorted(p.name for p in carpeta.glob("*.png")))


if __name__ == "__main__":
    main()
