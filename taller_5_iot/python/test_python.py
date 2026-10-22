#!/usr/bin/env python3
"""Checks de las funciones puras del Lab 5 (sin red, sin broker).
Correr:  python python/test_python.py   ->  esperado: "OK 3/3"
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import ingest  # noqa: E402
import publisher  # noqa: E402

# 1) payload: las 3 variables + ts en nanosegundos reales
p = json.loads(publisher.payload_json(
    lectura={"Temperature": 24.0, "Humidity": 50.0, "Iluminance": 400.0}))
assert set(p) == {"Temperature", "Humidity", "Iluminance", "ts_ns"}, p.keys()
assert isinstance(p["ts_ns"], int) and p["ts_ns"] > 10**18

# 2) modo caliente: temperatura SIEMPRE fuera del rango (para forzar la alerta)
st = {"Temperature": 24.0, "Humidity": 50.0, "Iluminance": 400.0}
for _ in range(200):
    lec = publisher.generar_lectura(caliente=True, state=st)
    assert 33.0 <= lec["Temperature"] <= 38.0, lec
    assert 35.0 <= lec["Humidity"] <= 70.0 and 100.0 <= lec["Iluminance"] <= 800.0
# y en modo normal NUNCA supera el umbral (la alerta no dispara sola)
for _ in range(500):
    assert publisher.generar_lectura(state=dict(st))["Temperature"] <= 32.0

# 3) linea de influx: measurement telemetria, campos float, ts ns intacto
line = ingest.to_line_protocol(
    {"Temperature": 24.1, "Humidity": 50.2, "Iluminance": 400.3,
     "ts_ns": 1700000000000000000})
assert line.startswith("telemetria,device=lab5 ")
assert "Temperature=24.1" in line and "Humidity=50.2" in line
assert line.endswith(" 1700000000000000000"), line

print("OK 3/3")
