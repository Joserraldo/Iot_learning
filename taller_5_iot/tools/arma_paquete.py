#!/usr/bin/env python3
"""arma_paquete.py — empaqueta SOLO lo necesario para que un LLM redacte el
informe del Lab 5. Nunca incluye secretos (.env, .pem) ni herramientas.
Salida: paquete-informe/ + paquete-informe-lab5.zip en la raíz del taller.
"""
import os
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "paquete-informe"
ZIP = ROOT / "paquete-informe-lab5.zip"

FILES = [
    "laboratorio_5.md",
    "informe-lab5.md",
    "docs/bitacora.md",
    "README.md",
    "docker/docker-compose.yml",
    "docker/grafana/provisioning/datasources/influx.yml",
    "docker/grafana/provisioning/alerting/lab5_rules.yml",
    "docker/grafana/dashboards/lab5.json",
    "python/publisher.py",
    "python/ingest.py",
    "python/test_python.py",
    "evidencias/forzamiento3.jsonl",
    "evidencias/alerta/grafana-alerta-vm2.log",
    "evidencias/alerta/dashboard-4d-con-datos.png",
]

CONTEXT = """# CONTEXTO PARA REDACTAR EL INFORME — Laboratorio 5 (IoT UNAB)

Eres el asistente que redacta el informe final del Laboratorio 5 de la
asignatura IoT + Cloud + Sistemas Distribuidos (UNAB). El estudiante es José
Andrés Téllez Rangel (u00060479).

## Qué pide la rúbrica (laboratorio_5.md)
- Protocolo elegido (MQTT/AMQP/CoAP) publicando Temperature/Humidity/Illuminance — 20%
- Grafana aparte (aislado de la BD), con la toma de 4 días visible — 30%
- Una alerta de umbral disparada y evidenciada — 25%
- Stack reproducible (docker-compose), informe único (1-2 páginas) y README — 25%

## Lo que se implementó
MQTT (eclipse-mosquitto) -> Ingestor Python -> InfluxDB 2.7 -> Grafana OSS 11.2
con provisioning como código, todo en Docker Compose sobre una VM Azure
(52.159.94.196), expuesto en https://iotcentraljose.duckdns.org/taller5/ y
/taller5/grafana/ con nginx + Let's Encrypt. Grafana lee la TSDB con un token
de solo lectura; la única escritora es el contenedor ingest.

## Datos reales de la toma (NO inventar otros)
- Ventana: 2026-10-17 04:51 UTC -> 2026-10-22 05:22 UTC (5 días, en bloques)
- 4 185 muestras a cadencia 60 s = 69.7 h de muestreo efectivo (58% de 120 h)
- Bloques ON: 17-oct 05-07 (173) | 17-oct 14 -> 18-oct 07 (1033) |
  18-oct 23 -> 19-oct 21 (1302) | 21-oct 02 -> 22-oct 05:22 (1677)
- Huecos: 17-oct 08-13 | 18-oct 08-22 | 19-oct 22 -> 21-oct 01
- Alerta >32 °C (media 10 min, for 2 min) disparada el 2026-10-17
  05:56:30-05:59:30 UTC con 60 mensajes forzados T=34.9-35.1 °C; notificación
  enviada por Brevo SMTP sin errores (grafana-alerta-vm2.log).
- Latencia PUBACK local ~0.5-1.7 ms; hop broker->ingestor ~0.6-1.3 ms.

## Cómo comportarse
1. Escribe en español, tono técnico y sobrio, sin relleno.
2. Usa SOLO los datos de los archivos adjuntos; si falta un dato, márcalo como
   "pendiente" en vez de inventarlo.
3. Mantén 1-2 páginas en el cuerpo principal; lo demás va en anexos.
4. Respeta las secciones que pide el enunciado: diagrama, justificación del
   protocolo, umbral de la alerta, ventana de 4 días (inicio, fin, huecos), qué
   falló al instalar.
"""


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "CONTEXTO.md").write_text(CONTEXT, encoding="utf-8")
    copied = ["CONTEXTO.md"]
    for rel in FILES:
        src = ROOT / rel
        if not src.exists():
            print("FALTA:", rel)
            continue
        dst = OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
        print("ok:", rel)
    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in copied:
            z.write(OUT / rel, rel)
    total = sum((OUT / r).stat().st_size for r in copied)
    print(f"\n{len(copied)} archivos, {total/1024:.0f} KB -> {ZIP.name}")


if __name__ == "__main__":
    main()
