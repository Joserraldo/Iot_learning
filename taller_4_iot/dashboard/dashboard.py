#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dashboard.py — Sala de control didáctica del Lab 4: MQTT · AMQP · CoAP -> Azure IoT Central.

Corre EN LA VM (vmtalleresjose · 52.237.172.24). Sirve:
  GET  /                     -> control room (tarjetas + comparativa + diagrama + evidencia)
  GET  /informe              -> página imprimible con la evidencia lista para el informe
  GET  /api/estado           -> estado en vivo de los 3 protocolos (JSON)
  GET  /api/capturas         -> capturas de evidencia hechas
  GET  /api/paquete.zip      -> zip con TODA la evidencia (jsonl + resumen + graficas + reporte)
  GET  /evidencias/<ruta>    -> descarga de archivos de evidencia
  POST /api/protocolo/<p>/iniciar|detener
  POST /api/todos/iniciar|detener
  POST /api/prueba/iniciar   -> corrida cronometrada (detiene, limpia y arranca los 3)
  POST /api/evidencia        -> "Capturar evidencia": snapshot + resumen + graficas + reporte.md

Las acciones de escritura piden la clave DASH_KEY (header X-Dash-Key o ?key=).
"""

from __future__ import annotations

import fcntl
import json
import os
import platform
import shutil
import subprocess
import threading
import time
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

from flask import (Flask, abort, jsonify, render_template, request, send_file,
                   send_from_directory)
from dotenv import dotenv_values

# ---------------------------------------------------------------- rutas / env
BASE = Path(__file__).resolve().parent.parent          # ~/taller_4_iot
VENV_PY = str(BASE / ".venv" / "bin" / "python")
EVID = BASE / "evidencias"
CAPTURAS = EVID / "capturas"
ESTADO_FILE = EVID / ".runs.json"
AUTOLOG = EVID / "autoreinicio.log"
WATCHDOG = os.environ.get("DASH_WATCHDOG", "1") not in ("0", "", "no", "false")
WATCHDOG_S = int(os.environ.get("DASH_WATCHDOG_S", "15"))
MAX_RSS_MB = int(os.environ.get("DASH_MAX_RSS_MB", "260"))
MAX_LOG_MB = int(os.environ.get("DASH_MAX_LOG_MB", "40"))
ENV = dotenv_values(BASE / ".env")

APP = Flask(__name__)
try:                                    # Flask >= 2.3
    APP.json.ensure_ascii = False
except Exception:                       # pragma: no cover
    APP.config["JSON_AS_ASCII"] = False

PROTOS = ("mqtt", "amqp", "coap")

LOG_LIVE = {
    "mqtt": EVID / "mqtt" / "live.jsonl",
    "amqp": EVID / "amqp" / "live.jsonl",
    "coap": EVID / "coap" / "live-client.jsonl",
}
LOG_GW = EVID / "coap" / "live-gw.jsonl"
LOG_STDOUT = {
    "mqtt": EVID / "mqtt" / "live.log",
    "amqp": EVID / "amqp" / "live.log",
    "coap": EVID / "coap" / "live-client.log",
    "coap-gw": EVID / "coap" / "live-gw.log",
}
PATRONES = {
    "mqtt": ["python/mqtt_baseline.py"],
    "amqp": ["python/amqp_sdk.py"],
    "coap": ["python/coap_client.py", "python/coap_gateway.py"],
}
SCRIPT = {
    "mqtt": "python/mqtt_baseline.py",
    "amqp": "python/amqp_sdk.py",
    "coap": "python/coap_client.py",
}
LAT_KEY = {"mqtt": "latency_ms", "amqp": "latency_ms", "coap": "rtt_ms"}
LAT_LABEL = {"mqtt": "PUBACK", "amqp": "disposition", "coap": "RTT CoAP"}
COLOR = {"mqtt": "#38bdf8", "amqp": "#a78bfa", "coap": "#34d399"}

# ---------------------------------------------------------------- didáctica
DIDACTICA = {
    "mqtt": {
        "titulo": "MQTT",
        "device": ENV.get("MQTT_DEVICE_ID", "mqtt-baseline-01"),
        "script": "python/mqtt_baseline.py",
        "puerto": "8883",
        "transporte": "TCP + TLS 1.2/1.3",
        "modelo": "pub/sub por topics",
        "fiabilidad": "QoS 1 → PUBACK del hub",
        "destino": "Azure IoT Central (nativo)",
        "tls": "sí · TLS 1.2/1.3",
        "variable_medida": "PUBACK",
        "resumen": ("Cliente MQTT EXPLÍCITO (paho, sin SDK): abre TCP+TLS al hub, "
                    "se autentica con SAS token y publica el JSON en "
                    "devices/{id}/messages/events/. Mide publish → PUBACK."),
        "ciclo": ["CONNECT + TLS", "CONNACK", "PUBLISH QoS1", "PUBACK ← hub"],
        "capas": [
            ("Aplicación", "MQTT 3.1.1 · PUBLISH al topic devices/{id}/messages/events/"),
            ("Transporte", "TCP · conexión persistente (el hub puede cerrarla, paho reconecta)"),
            ("Seguridad", "TLS 1.2/1.3 (certificado del hub) + SAS token en el CONNECT"),
            ("Red", "IP · puerto 8883"),
        ],
        "cable": {"payload": 60, "cabecera": 2,
                  "nota": "cabecera fija MQTT de 2 B; el topic, las tramas TCP y el registro TLS van aparte"},
        "secuencia": [
            {"dir": "→", "texto": "TCP + handshake TLS 1.2/1.3 + CONNECT con SAS", "ms": None,
             "nota": "solo la primera vez"},
            {"dir": "←", "texto": "CONNACK (el hub acepta la sesión)", "ms": None},
            {"dir": "→", "texto": "PUBLISH QoS 1 · 60 B de telemetría", "ms": None},
            {"dir": "←", "texto": "PUBACK del hub", "ms": "last", "etiqueta": "puback"},
        ],
        "kpi": ("PUBACK = tiempo desde que el cliente publica hasta que el hub confirma que el mensaje "
                "quedó en cola (QoS 1). No incluye la entrega a la app: MQTT desacopla emisor y receptor."),
        "nota_seq": "el handshake TLS y el CONNECT solo se pagan una vez, al arrancar la corrida",
        "cuando": "telemetría ligera de muchos dispositivos y MCU (ESP32): soporte maduro y debug fácil.",
        "cards": [
            ("Overhead", "cabecera MQTT mínima (2 B fijos) sobre TCP"),
            ("Firewall", "8883 a veces bloqueado; salida típica por 443/WS"),
            ("MCU / ESP32", "soporte maduro (paho, Arduino, Wokwi)"),
            ("Debug", "el más fácil: mosquitto_sub / Wireshark"),
        ],
    },
    "amqp": {
        "titulo": "AMQP 1.0",
        "device": ENV.get("AMQP_DEVICE_ID", "amqp-lab4-01"),
        "script": "python/amqp_sdk.py",
        "puerto": "5671",
        "transporte": "TCP + TLS (AMQP 1.0 binario)",
        "modelo": "peer-to-peer con links y créditos",
        "fiabilidad": "disposition SendComplete (accepted)",
        "destino": "Azure IoT Central / IoT Hub (nativo)",
        "tls": "sí · TLS 1.2/1.3",
        "variable_medida": "disposition",
        "resumen": ("Cliente AMQP 1.0 EXPLÍCITO (uamqp): el SDK 2.x ya no trae AMQP. "
                    "TLS 5671, auth CBS (put-token al nodo $cbs), attach del link de "
                    "envío a amqps://{hub}/devices/{id}/messages/events y disposition."),
        "ciclo": ["TCP + TLS", "CBS put-token ($cbs)", "attach link de envío",
                  "TRANSFER → disposition accepted"],
        "capas": [
            ("Aplicación", "AMQP 1.0 · transfer al endpoint devices/{id}/messages/events"),
            ("Sesión / link", "attach del link de envío + créditos (control de flujo)"),
            ("Transporte", "TCP · sesión con estado"),
            ("Seguridad", "TLS + auth CBS (put-token del SAS al nodo $cbs)"),
            ("Red", "IP · puerto 5671"),
        ],
        "cable": {"payload": 60, "cabecera": 8,
                  "nota": "cabecera fija AMQP de 8 B; lo caro de AMQP no es el dato, es el handshake"},
        "secuencia": [
            {"dir": "→", "texto": "TCP + TLS 1.2/1.3", "ms": None, "nota": "primera vez"},
            {"dir": "→", "texto": "CBS put-token: se presenta el SAS token", "ms": None, "nota": "nodo $cbs"},
            {"dir": "→", "texto": "attach del link de envío + crédito", "ms": None},
            {"dir": "→", "texto": "TRANSFER · 60 B de telemetría", "ms": None},
            {"dir": "←", "texto": "disposition accepted", "ms": "last", "etiqueta": "SendComplete"},
        ],
        "kpi": ("disposition = el hub acepta el mensaje y se hace responsable de entregarlo (garantía "
                "explícita por mensaje). Con el link ya abierto el costo por mensaje es solo el transfer; "
                "el 1er mensaje paga TLS + CBS + attach."),
        "nota_seq": "el 1er mensaje de cada corrida paga TLS + CBS + attach (~430-570 ms medidos); después solo el transfer",
        "cuando": "mensajería entre servicios Azure (Service Bus, Event Hubs) y plataformas propias: "
                  "sesiones, créditos y garantías de entrega que MQTT no da.",
        "cards": [
            ("Overhead", "handshake pesado (TLS+CBS+attach ≈ 430 ms la 1ª vez)"),
            ("Firewall", "5671 / 443 con AMQP sobre WebSockets"),
            ("MCU / ESP32", "poco usado en microcontroladores"),
            ("Debug", "medio: frames binarios AMQP, traza con --debug"),
        ],
    },
    "coap": {
        "titulo": "CoAP (UDP)",
        "device": ENV.get("COAP_DEVICE_ID", "coap-gateway-01"),
        "script": "python/coap_client.py + python/coap_gateway.py",
        "puerto": "5683/udp",
        "transporte": "UDP (sin TLS en el salto CoAP)",
        "modelo": "request/response con mensajes CON",
        "fiabilidad": "2.04 Changed + retransmisión CON (RFC 7252)",
        "destino": "gateway propio en la VM → puente MQTT → Central",
        "tls": "no en el salto CoAP · sí en el puente",
        "variable_medida": "RTT CoAP",
        "resumen": ("CoAP NO es nativo de IoT Central. El nodo constrained POSTea el JSON "
                    "a coap://127.0.0.1:5683/telemetry; el gateway responde 2.04 Changed y "
                    "reenvía la telemetría a Central por su propio cliente SDK. Se mide el "
                    "RTT del datagrama y la latencia de forwarding del gateway."),
        "ciclo": ["POST CON (UDP 60 B)", "gateway recibe + valida",
                  "puente MQTT → Central (ack)", "2.04 Changed ← gateway"],
        "capas": [
            ("Aplicación", "CoAP (RFC 7252) · POST /telemetry con JSON"),
            ("Transporte", "UDP · sin conexión (mensaje CON con retransmisión)"),
            ("Seguridad", "sin TLS en el salto CoAP (DTLS es opcional y aquí no se usa)"),
            ("Red", "IP · puerto 5683/udp"),
            ("Puente", "gateway propio → cliente SDK (MQTT 8883) → IoT Central"),
        ],
        "cable": {"payload": 60, "cabecera": 4,
                  "nota": "cabecera fija CoAP de 4 B + UDP: el mensaje más liviano de los tres, sin handshake"},
        "secuencia": [
            {"dir": "→", "texto": "POST CON · cabecera 4 B + 60 B (datagrama UDP)", "ms": None,
             "nota": "sin handshake"},
            {"dir": "→", "texto": "el gateway valida el JSON y lo reenvía con su cliente SDK",
             "ms": "gw_last", "etiqueta": "forwarding"},
            {"dir": "←", "texto": "2.04 Changed (confirmación CoAP)", "ms": "last", "etiqueta": "RTT"},
        ],
        "kpi": ("RTT = ida y vuelta del datagrama al gateway (que corre en la misma VM). El forwarding "
                "mide lo que tarda el gateway en reenviarlo a Central: por eso el salto CoAP/UDP local "
                "es submilisegundo y casi todo el tiempo es el tramo a Azure."),
        "nota_seq": "no hay handshake: cada POST es un datagrama independiente que viaja solo",
        "cuando": "nodos muy constrained en red local (batería, radio LPWAN) con un gateway que haga de puente.",
        "cards": [
            ("Overhead", "cabecera CoAP mínima (4 B) + UDP sin TLS"),
            ("Firewall", "UDP 5683 suele pasar, sin garantía"),
            ("MCU / ESP32", "ideal constrained (RFC 7252)"),
            ("Debug", "medio-fácil: mensajes pequeños, aiocoap -v"),
        ],
    },
}

# ---------------------------------------------------------------- glosario
GLOSARIO = [
    ("QoS 1 → PUBACK", "MQTT: el hub confirma al cliente que recibió el mensaje (garantía «al menos una vez»)."),
    ("Topic", "MQTT: la dirección del mensaje (devices/{id}/messages/events/). El broker enruta por ahí y el emisor no conoce al receptor."),
    ("Link + créditos", "AMQP: canal de envío con control de flujo; el emisor no puede inundar al receptor."),
    ("disposition / SendComplete", "AMQP: respuesta del hub mensaje por mensaje («accepted»). Es el equivalente al PUBACK, pero a nivel de enlace."),
    ("CBS ($cbs)", "AMQP: nodo del hub donde el dispositivo presenta su SAS token antes de enviar telemetría."),
    ("CON y 2.04 Changed", "CoAP: CON = mensaje confirmable que espera respuesta; 2.04 Changed = el recurso se actualizó bien."),
    ("UDP vs TCP", "CoAP viaja sobre UDP (sin conexión ni handshake); MQTT y AMQP sobre TCP+TLS (conexión persistente)."),
    ("Gateway", "Componente intermedio: recibe CoAP -que IoT Central no habla nativo- y lo reenvía con su propio cliente SDK."),
    ("SAS token", "Credencial firmada con HMAC-SHA256 que autentica al dispositivo. Se construye en memoria y nunca va al repo."),
    ("Handshake TLS", "Negociación inicial del canal cifrado. Se paga una sola vez: en AMQP explica que el primer mensaje tarde ~500 ms."),
    ("Datagrama", "Unidad independiente de UDP: cabe entera en un paquete y no requiere conexión previa."),
    ("Device y plantilla", "En IoT Central la plantilla (consola-unab-ambiental) define las 3 variables; cada device es una identidad con su key."),
]

APP_INFO = {
    "app": ENV.get("IOT_CENTRAL_APP", "clima-salones-app-jose.azureiotcentral.com"),
    "vm": "vmtalleresjose · 52.237.172.24 · North Central US",
    "url": "https://iotcentraljose.duckdns.org",
    "estudiante": "José Alejandro Téllez Prada",
    "materia": "IoT + Cloud + Sistemas Distribuidos · UNAB · Lab 4",
}


def dash_key() -> str:
    return (os.environ.get("DASH_KEY") or ENV.get("DASH_KEY") or "").strip()


def clave_ok() -> bool:
    k = dash_key()
    if not k:
        return True
    dada = (request.headers.get("X-Dash-Key")
            or request.args.get("key")
            or (request.get_json(silent=True) or {}).get("key", ""))
    return str(dada).strip() == k


# ---------------------------------------------------------------- helpers SO
def pids(patron: str) -> list[int]:
    r = subprocess.run(["pgrep", "-f", patron], capture_output=True, text=True)
    return [int(x) for x in r.stdout.split()] if r.returncode == 0 else []


def corriendo(p: str) -> list[int]:
    out: list[int] = []
    for pat in PATRONES[p]:
        out += pids(pat)
    return out


def matar(p: str) -> None:
    for pat in PATRONES[p]:
        subprocess.run(["pkill", "-9", "-f", pat], capture_output=True)
    for _ in range(20):                        # espera a que suelten CPU/puertos
        if not corriendo(p):
            break
        time.sleep(0.2)


def leer_estado_disco() -> dict:
    try:
        return json.loads(ESTADO_FILE.read_text())
    except Exception:
        return {}


def guardar_estado_disco(d: dict) -> None:
    EVID.mkdir(parents=True, exist_ok=True)
    ESTADO_FILE.write_text(json.dumps(d, indent=2))


# ---------------------------------------------------------------- lectura logs
_cache_lineas: dict[str, tuple[int, int]] = {}


def contar_lineas(path: Path) -> int:
    """Cuenta líneas de forma INCREMENTAL.

    En un log que crece sin parar, recontarlo entero en cada refresco (cada 2,5 s)
    se vuelve O(tamaño) y con semanas de datos sería inviable: aquí solo se leen
    los bytes nuevos desde la última cuenta.
    """
    try:
        st = path.stat()
    except FileNotFoundError:
        _cache_lineas.pop(str(path), None)
        return 0
    prev = _cache_lineas.get(str(path))
    total, desde = 0, 0
    if prev and 0 <= prev[0] <= st.st_size:          # el archivo no se truncó
        total, desde = prev[1], prev[0]
    if desde == st.st_size:
        return total
    with open(path, "rb") as fh:
        fh.seek(desde)
        while True:
            bloque = fh.read(1 << 20)
            if not bloque:
                break
            total += bloque.count(b"\n")
    _cache_lineas[str(path)] = (st.st_size, total)
    return total


def leer_tail_jsonl(path: Path, max_bytes: int = 400_000) -> list[dict]:
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return []
    recs: list[dict] = []
    with open(path, "rb") as f:
        if size > max_bytes:
            f.seek(size - max_bytes)
            f.readline()                        # descarta la línea partida
        data = f.read().decode("utf-8", errors="replace")
    for linea in data.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            recs.append(json.loads(linea))
        except json.JSONDecodeError:
            pass
    return recs


def tail_texto(path: Path, n: int = 8, max_bytes: int = 40_000) -> list[str]:
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return []
    with open(path, "rb") as f:
        if size > max_bytes:
            f.seek(size - max_bytes)
            f.readline()
        data = f.read().decode("utf-8", errors="replace")
    return [l for l in data.splitlines() if l.strip()][-n:]


def ts_ms(iso: str) -> int | None:
    try:
        return int(datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
                   .replace(tzinfo=timezone.utc).timestamp() * 1000)
    except Exception:
        return None


def metricas(path: Path, lat_key: str, ventana: int = 0) -> dict:
    """ventana>0 => solo las últimas N muestras (para los KPIs en vivo)."""
    recs = leer_tail_jsonl(path)
    if ventana:
        recs = recs[-ventana:]
    vals = [r[lat_key] for r in recs if isinstance(r.get(lat_key), (int, float))]
    ult = recs[-1] if recs else {}
    return {
        "total": contar_lineas(path),
        "n_ventana": len(recs),
        "n_lat": len(vals),
        "avg": round(sum(vals) / len(vals), 1) if vals else None,
        "min": round(min(vals), 1) if vals else None,
        "max": round(max(vals), 1) if vals else None,
        "last": round(vals[-1], 1) if vals else None,
        "primero": round(vals[0], 1) if vals else None,
        "bytes": ult.get("bytes"),
        "seq": ult.get("seq"),
        "payload": ult.get("payload"),
        "t": ult.get("t"),
        "outcome": ult.get("outcome"),
        "code": ult.get("code"),
        "serie": [[ts_ms(r["t"]), r[lat_key]] for r in recs
                  if isinstance(r.get(lat_key), (int, float)) and r.get("t")][-60:],
    }


def metricas_completas(path: Path, lat_key: str) -> dict:
    """Todas las muestras del archivo (para capturar evidencia)."""
    recs = leer_tail_jsonl(path, max_bytes=8_000_000)
    vals = [r[lat_key] for r in recs if isinstance(r.get(lat_key), (int, float))]
    m = {
        "n": len(recs),
        "n_lat": len(vals),
        "avg": round(sum(vals) / len(vals), 1) if vals else None,
        "min": round(min(vals), 1) if vals else None,
        "max": round(max(vals), 1) if vals else None,
        "bytes": sum(r.get("bytes", 0) for r in recs),
        "bytes_msg": recs[-1].get("bytes") if recs else None,
        "desde": recs[0].get("t") if recs else None,
        "hasta": recs[-1].get("t") if recs else None,
    }
    if len(vals) > 1:                            # AMQP: 1er msg = handshake
        resto = vals[1:]
        m["avg_sin_primero"] = round(sum(resto) / len(resto), 1)
        m["primero"] = round(vals[0], 1)
    marcas = [x for x in (ts_ms(r.get("t", "")) for r in recs) if x]
    if len(marcas) > 2:                          # intervalo real observado
        difs = sorted(d for d in ((b - a) / 1000.0 for a, b in zip(marcas, marcas[1:]))
                      if 0 < d < 600)
        if difs:
            m["intervalo_obs"] = round(difs[len(difs) // 2], 1)
    return m


# ---------------------------------------------------------------- vigilante
def _log_vigilante(msg: str) -> None:
    try:
        EVID.mkdir(parents=True, exist_ok=True)
        with open(AUTOLOG, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} {msg}\n")
    except OSError:
        pass


def rss_mb(pids_: list[int]) -> float:
    """Memoria residente (RSS) sumada de los procesos, leída de /proc."""
    total = 0
    for pid in pids_:
        try:
            with open(f"/proc/{pid}/statm", encoding="utf-8") as fh:
                total += int(fh.read().split()[1]) * 4096
        except (OSError, ValueError, IndexError):
            pass
    return round(total / 1048576, 1)


def rotar_si_grande(path: Path) -> None:
    """Un log que crece para siempre termina llenando el disco: si pasa el tope, se vacía.
    Es seguro: los scripts escriben con O_APPEND, así que siguen escribiendo al final."""
    try:
        mb = path.stat().st_size / 1048576
    except OSError:
        return
    if mb > MAX_LOG_MB:
        with open(path, "wb"):
            pass
        _log_vigilante(f"rotado {path.name}: tenía {mb:.0f} MB (tope {MAX_LOG_MB} MB)")


def vigilante() -> None:
    """Hilo de fondo (uno solo, garantizado con flock): si un cliente se cae o se pasa
    de memoria, lo relanza él mismo para que la página no quede a medias en una clase.
    No toca nada mientras hay una acción manual reciente ni dentro del backoff."""
    candado = None
    while True:
        if candado is None:
            try:
                candado = open(EVID / ".watchdog.lock", "w")
                fcntl.flock(candado, fcntl.LOCK_EX | fcntl.LOCK_NB)
                _log_vigilante("vigilante iniciado")
            except OSError:
                if candado:                      # otro worker lo tiene: reintentar pronto
                    candado.close()
                candado = None
                time.sleep(20)
                continue
            time.sleep(3)                        # primera pasada casi inmediata
        time.sleep(WATCHDOG_S)
        try:
            st = leer_estado_disco()
            ahora = time.time()
            for p in PROTOS:
                e = st.get(p)
                if not e:
                    continue
                if ahora - e.get("ultima_accion", 0) < 25:      # hay una acción manual en curso
                    continue
                if ahora - e.get("ultimo_reinicio", 0) < 60:    # backoff: no reiniciar en bucle
                    continue
                iv = float(e.get("intervalo") or 3)
                vivos = corriendo(p)
                mb = rss_mb(vivos)
                caido = not vivos
                gordo = mb > MAX_RSS_MB
                if caido or gordo:
                    motivo = "proceso caído" if caido else f"consumo alto ({mb} MB)"
                    matar(p)
                    if p == "coap":
                        lanzar_gateway(truncar=False)
                        time.sleep(3)
                    lanzar(p, iv, truncar=False)
                    e["ultimo_reinicio"] = ahora
                    e["reinicios"] = int(e.get("reinicios", 0)) + 1
                    guardar_estado_disco(st)
                    _log_vigilante(f"reinicio {p}: {motivo} (nº {e['reinicios']}, sigue la corrida)")
                    continue
                if p == "coap" and not pids("python/coap_gateway.py"):
                    lanzar_gateway(truncar=False)
                    _log_vigilante("reinicio del gateway CoAP (no estaba escuchando)")
            for ruta in list(LOG_LIVE.values()) + [LOG_GW] + list(LOG_STDOUT.values()):
                rotar_si_grande(ruta)
        except Exception as ex:                                  # el vigilante nunca debe morir
            _log_vigilante(f"error del vigilante: {type(ex).__name__}: {ex}")


# ---------------------------------------------------------------- estado API
def estado_protocolo(p: str) -> dict:
    runs = leer_estado_disco().get(p, {})
    run_pids = corriendo(p)
    m = metricas(LOG_LIVE[p], LAT_KEY[p], ventana=0)
    cons = tail_texto(LOG_STDOUT[p], 8)
    err = ""
    for linea in reversed(tail_texto(LOG_STDOUT[p], 60)):
        if any(k in linea for k in ("Traceback", "Error", "ERROR", "TIMEOUT",
                                    "Exception", "refused", "Failure")):
            err = linea.strip()
            break
    d = {
        "id": p,
        "corriendo": bool(run_pids),
        "pids": run_pids,
        "inicio": runs.get("inicio"),
        "duracion": (round(time.time() - runs["inicio"]) if runs.get("inicio") else None),
        "intervalo": runs.get("intervalo"),
        "reinicios": int(runs.get("reinicios", 0) or 0),
        "memoria_mb": rss_mb(run_pids),
        "metrica": m,
        "consola": cons,
        "ultimo_error": err,
    }
    if p == "coap":
        g = metricas(LOG_GW, "forward_latency_ms", ventana=0)
        d["gateway"] = {
            "corriendo": bool(pids("python/coap_gateway.py")),
            "metrica": g,
            "consola": tail_texto(LOG_STDOUT["coap-gw"], 6),
        }
        # el nodo CoAP no guarda el payload en su log: se muestra el que vio el gateway
        if not d["metrica"].get("payload") and g.get("payload"):
            d["metrica"]["payload"] = g["payload"]
            d["metrica"]["bytes"] = g.get("bytes")
            d["metrica"]["seq"] = g.get("seq")
            d["metrica"]["t"] = g.get("t")
            d["metrica"]["payload_de"] = "gateway"
    return d


@APP.route("/api/estado")
def api_estado():
    datos = {p: estado_protocolo(p) for p in PROTOS}
    return jsonify({
        "ahora": int(time.time() * 1000),
        "uptime": round(time.time() - ARRANQUE),
        "protocolos": datos,
        "meta": DIDACTICA,
        "info": APP_INFO,
        "clave_requerida": bool(dash_key()),
    })


# ---------------------------------------------------------------- acciones
def lanzar(p: str, intervalo: float, duration: int = 0, truncar: bool = True) -> None:
    """Lanza el cliente DETACHED sin bloquear la petición HTTP.

    Clave: `exec setsid ...` + Popen con los fd en DEVNULL. Con `nohup ... &`
    el subshell de fondo queda vivo (es el padre del script) y retenía el pipe
    de salida del subprocess -> la petición se colgaba hasta que el script moría.
    """
    log = LOG_LIVE[p].relative_to(BASE)
    stdout = LOG_STDOUT[p].relative_to(BASE)
    script = SCRIPT[p]
    borrar = f"rm -f {log} && " if truncar else ""     # el vigilante NO borra: conserva la evidencia
    cmd = (f"cd {BASE} && {borrar}exec setsid {VENV_PY} -u {script} "
           f"--duration {duration} --interval {intervalo} --log {log} "
           f"> {stdout} 2>&1 < /dev/null")
    subprocess.Popen(["bash", "-c", cmd], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def lanzar_gateway(truncar: bool = True) -> None:
    log = LOG_GW.relative_to(BASE)
    stdout = LOG_STDOUT["coap-gw"].relative_to(BASE)
    borrar = f"rm -f {log} && " if truncar else ""
    cmd = (f"cd {BASE} && {borrar}exec setsid {VENV_PY} -u "
           f"python/coap_gateway.py --log {log} "
           f"> {stdout} 2>&1 < /dev/null")
    subprocess.Popen(["bash", "-c", cmd], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def iniciar(p: str, intervalo: float) -> dict:
    matar(p)                                  # limpia restos (incluye gateway CoAP)
    time.sleep(0.4)
    if p == "coap":
        lanzar_gateway()
        time.sleep(3)                         # el gateway debe escuchar antes del nodo
    lanzar(p, intervalo)
    st = leer_estado_disco()
    st[p] = {"inicio": time.time(), "intervalo": intervalo,
             "ultima_accion": time.time(), "reinicios": 0}
    guardar_estado_disco(st)
    return {"ok": True, "protocolo": p, "iniciado": True, "intervalo": intervalo}


@APP.route("/api/protocolo/<p>/iniciar", methods=["POST"])
def api_iniciar(p: str):
    if p not in PROTOS:
        abort(404)
    if not clave_ok():
        return jsonify({"ok": False, "error": "clave requerida"}), 401
    iv = float((request.get_json(silent=True) or {}).get("intervalo") or 3)
    return jsonify(iniciar(p, iv))


@APP.route("/api/protocolo/<p>/detener", methods=["POST"])
def api_detener(p: str):
    if p not in PROTOS:
        abort(404)
    if not clave_ok():
        return jsonify({"ok": False, "error": "clave requerida"}), 401
    matar(p)
    st = leer_estado_disco()
    st.pop(p, None)
    guardar_estado_disco(st)
    return jsonify({"ok": True, "protocolo": p, "detenido": True})


@APP.route("/api/todos/iniciar", methods=["POST"])
def api_todos_iniciar():
    if not clave_ok():
        return jsonify({"ok": False, "error": "clave requerida"}), 401
    iv = float((request.get_json(silent=True) or {}).get("intervalo") or 3)
    return jsonify({p: iniciar(p, iv) for p in PROTOS})


@APP.route("/api/todos/detener", methods=["POST"])
def api_todos_detener():
    if not clave_ok():
        return jsonify({"ok": False, "error": "clave requerida"}), 401
    for p in PROTOS:
        matar(p)
    guardar_estado_disco({})
    return jsonify({"ok": True, "detenidos": list(PROTOS)})


@APP.route("/api/prueba/iniciar", methods=["POST"])
def api_prueba():
    """Corrida cronometrada: limpia los logs, arranca los 3 y marca el t0."""
    if not clave_ok():
        return jsonify({"ok": False, "error": "clave requerida"}), 401
    cuerpo = request.get_json(silent=True) or {}
    iv = float(cuerpo.get("intervalo") or 10)
    seg = int(cuerpo.get("segundos") or 90)
    for p in PROTOS:
        matar(p)
    time.sleep(0.5)
    for p in PROTOS:
        if p == "coap":
            lanzar_gateway()
            time.sleep(3)
        lanzar(p, iv)
    t0 = time.time()
    guardar_estado_disco({p: {"inicio": t0, "intervalo": iv, "prueba": seg,
                              "ultima_accion": t0, "reinicios": 0} for p in PROTOS})
    return jsonify({"ok": True, "t0": int(t0 * 1000), "segundos": seg,
                    "intervalo": iv})


# ---------------------------------------------------------------- evidencia
def generar_markdown(cap: dict) -> str:
    P = cap["protocolos"]
    l = []
    a = l.append
    a(f"# Evidencia Lab 4 — captura {cap['ts_label']}")
    a("")
    a(f"- **App IoT Central:** `{APP_INFO['app']}`")
    a(f"- **VM:** {APP_INFO['vm']}  ·  `{platform.platform()}`")
    a(f"- **Estudiante:** {APP_INFO['estudiante']}")
    a(f"- **Captura (UTC):** {cap['iso']}")
    a(f"- **Intervalo de publicación:** {cap['intervalo']} s")
    if cap.get("nota"):
        a(f"- **Nota:** {cap['nota']}")
    a("")
    a("## 1. Telemetría publicada por protocolo (datos de esta captura)")
    a("")
    a("| Protocolo | Device | Dónde corre | Endpoint destino | Puerto | Transporte | TLS | n | Latencia prom | min | max | Bytes/msg |")
    a("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for p in PROTOS:
        d = DIDACTICA[p]
        m = P[p]
        a(f"| **{d['titulo']}** | `{d['device']}` | VM | {d['destino']} | {d['puerto']} | "
          f"{d['transporte']} | {d['tls']} | "
          f"{m['n']} | **{m['avg']} ms** | {m['min']} | {m['max']} | {m['bytes_msg']} B |")
    a("")
    if P["amqp"].get("avg_sin_primero") is not None:
        a(f"> **AMQP:** el primer mensaje ({P['amqp'].get('primero')} ms) incluye el handshake "
          f"(TLS + CBS + attach). En estado estacionario: **{P['amqp']['avg_sin_primero']} ms**.")
        a("")
    if P.get("coap_gw"):
        g = P["coap_gw"]
        a(f"> **CoAP:** RTT del datagrama promedio **{P['coap']['avg']} ms**; el *forwarding* "
          f"del gateway hacia Central promedió **{g['avg']} ms** "
          f"(n={g['n']}). El salto CoAP/UDP local es submilisegundo.")
        a("")
    a("## 2. Variables y formato del mensaje")
    a("")
    a("Los tres clientes publican las MISMAS 3 variables de la plantilla "
      "`consola-unab-ambiental`, con el mismo formato JSON plano (1 decimal, 60 B):")
    a("")
    a("```json")
    a('{"Temperature": 20.1, "Humidity": 47.5, "Iluminance": 400.3}')
    a("```")
    a("")
    a("## 3. Ciclo de comunicación observado")
    a("")
    for p in PROTOS:
        a(f"- **{DIDACTICA[p]['titulo']}:** " + " → ".join(DIDACTICA[p]["ciclo"]))
    a("")
    a("## 3b. Cómo viaja el mensaje, protocolo por protocolo")
    a("")
    for p in PROTOS:
        d = DIDACTICA[p]
        a(f"### {d['titulo']} — device `{d['device']}`")
        a("")
        a("| Capa | Qué hace |")
        a("|---|---|")
        for capa, det in d["capas"]:
            a(f"| **{capa}** | {det} |")
        a("")
        a(f"**Peso del mensaje:** {d['cable']['payload']} B de datos + **{d['cable']['cabecera']} B** "
          f"de cabecera fija. {d['cable']['nota']} · {d['nota_seq']}.")
        a("")
        a("**Secuencia:**")
        a("")
        for i, s in enumerate(d["secuencia"], 1):
            extra = f" *({s['nota']})*" if s.get("nota") else ""
            a(f"{i}. `{s['dir']}` {s['texto']}{extra}")
        a("")
        a(f"**Qué mide la latencia reportada:** {d['kpi']}")
        a("")
        a(f"**Cuándo usarlo:** {d['cuando']}")
        a("")
    a("## 4. Tabla comparativa (teórico vs observado en la VM)")
    a("")
    a("| Criterio | MQTT | AMQP 1.0 | CoAP (UDP) |")
    a("|---|---|---|---|")
    a("| Modelo | pub/sub (topics) | peer-to-peer (links + créditos) | request/response (CON) |")
    a("| Puerto / transporte | 8883 TCP+TLS | 5671 TCP+TLS | 5683 UDP |")
    a(f"| Latencia observada | {P['mqtt']['avg']} ms | {P['amqp']['avg']} ms"
      f"{' (steady ' + str(P['amqp'].get('avg_sin_primero')) + ' ms)' if P['amqp'].get('avg_sin_primero') else ''} | "
      f"{P['coap']['avg']} ms (RTT) + {P['coap_gw']['avg'] if P.get('coap_gw') else '-'} ms (forwarding) |")
    a("| Fiabilidad | PUBACK QoS1 | disposition `SendComplete` | 2.04 Changed + retransmisión CON |")
    a("| Overhead | cabecera mínima + TLS | handshake pesado (TLS+CBS+attach) | cabecera mínima, UDP sin TLS |")
    a("| Firewall/NAT | 8883 a veces bloqueado (443/WS) | 5671 / 443 AMQP-WS | UDP 5683 suele pasar, sin garantía |")
    a("| MCU / ESP32 | soporte maduro | poco usado | ideal constrained |")
    a("| IoT Central | nativo | nativo | **requiere gateway propio** |")
    a("| Debug | muy fácil | medio (frames binarios) | medio-fácil |")
    a("")
    a("## 5. Evidencia cruda")
    a("")
    for f in cap["archivos"]:
        a(f"- `{f}`")
    a("")
    a("---")
    a(f"Generado automáticamente por `dashboard/dashboard.py` el {cap['iso_local']}.")
    return "\n".join(l)


def capturar(nota: str = "") -> dict:
    ts_label = datetime.now(timezone(timedelta(hours=-5))).strftime("%Y-%m-%d %H:%M:%S -05")
    ts = datetime.now(timezone(timedelta(hours=-5))).strftime("%Y%m%d-%H%M%S")
    carpeta = CAPTURAS / f"captura-{ts}"
    carpeta.mkdir(parents=True, exist_ok=True)
    globals()["ULTIMA_CAPTURA"] = f"capturas/{carpeta.name}"

    runs = leer_estado_disco()
    intervalo = (runs.get("mqtt", {}) or {}).get("intervalo")
    cap = {
        "ts": ts,
        "ts_label": ts_label,
        "iso": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "iso_local": ts_label,
        "intervalo": intervalo,
        "nota": nota,
        "vm": APP_INFO["vm"],
        "app": APP_INFO["app"],
        "os": platform.platform(),
        "protocolos": {},
        "archivos": [],
    }
    for p in PROTOS:
        cap["protocolos"][p] = metricas_completas(LOG_LIVE[p], LAT_KEY[p])
        pares = [(f"{p}.jsonl", LOG_LIVE[p]), (f"{p}-stdout.log", LOG_STDOUT[p])]
        if p == "coap":
            pares.append(("coap-gateway.jsonl", LOG_GW))
            pares.append(("coap-gateway-stdout.log", LOG_STDOUT["coap-gw"]))
        for nombre, src in pares:
            if src.exists() and src.stat().st_size:
                shutil.copy2(src, carpeta / nombre)
                cap["archivos"].append(f"{carpeta.name}/{nombre}")
    cap["protocolos"]["coap_gw"] = metricas_completas(LOG_GW, "forward_latency_ms")
    if not intervalo:                            # corrida no lanzada desde el panel
        intervalo = cap["protocolos"]["mqtt"].get("intervalo_obs") or \
                    cap["protocolos"]["amqp"].get("intervalo_obs") or "?"
    cap["intervalo"] = intervalo

    (carpeta / "resumen.json").write_text(json.dumps(cap, indent=2, ensure_ascii=False))
    (carpeta / "reporte.md").write_text(generar_markdown(cap), encoding="utf-8")
    cap["archivos"] += [f"{carpeta.name}/resumen.json", f"{carpeta.name}/reporte.md"]

    r = subprocess.run([VENV_PY, str(Path(__file__).parent / "hacer_graficas.py"),
                        str(carpeta)], capture_output=True, text=True, timeout=180)
    cap["graficas_ok"] = r.returncode == 0
    cap["graficas_msg"] = (r.stdout + r.stderr).strip()[-400:] if r.returncode else ""
    if cap["graficas_ok"]:
        for png in sorted(carpeta.glob("*.png")):
            cap["archivos"].append(f"{carpeta.name}/{png.name}")
    cap["carpeta"] = carpeta.name
    return cap


@APP.route("/api/evidencia", methods=["POST"])
def api_evidencia():
    if not clave_ok():
        return jsonify({"ok": False, "error": "clave requerida"}), 401
    cuerpo = request.get_json(silent=True) or {}
    cap = capturar(str(cuerpo.get("nota") or ""))
    return jsonify({"ok": True, "captura": cap})


@APP.route("/api/capturas")
def api_capturas():
    if not CAPTURAS.exists():
        return jsonify({"capturas": []})
    out = []
    for d in sorted(CAPTURAS.iterdir(), reverse=True):
        if d.is_dir():
            out.append({
                "nombre": d.name,
                "archivos": sorted(f.name for f in d.iterdir()),
                "pngs": sorted(f.name for f in d.glob("*.png")),
                "mtime": d.stat().st_mtime,
            })
    return jsonify({"capturas": out, "ultima": globals().get("ULTIMA_CAPTURA")})


@APP.route("/api/paquete.zip")
def api_zip():
    CAPTURAS.mkdir(parents=True, exist_ok=True)
    destino = CAPTURAS / "paquete-evidencias-lab4.zip"
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for carpeta in sorted(CAPTURAS.iterdir()):
            if carpeta.is_dir():
                for f in carpeta.rglob("*"):
                    if f.is_file():
                        z.write(f, f.relative_to(EVID))
        for p in PROTOS:
            for f in (EVID / p).glob("vm-*.jsonl"):
                z.write(f, f.relative_to(EVID))
    return send_file(destino, as_attachment=True,
                     download_name="evidencias-lab4.zip")


@APP.route("/evidencias/<path:rel>")
def descargar(rel: str):
    destino = (EVID / rel).resolve()
    if not str(destino).startswith(str(EVID.resolve())) or not destino.exists():
        abort(404)
    return send_from_directory(EVID, rel, as_attachment=destino.is_file())


# ---------------------------------------------------------------- vistas
@APP.route("/")
def raiz():
    return render_template("index.html", meta=DIDACTICA, info=APP_INFO,
                           color=COLOR, clave=bool(dash_key()), glosario=GLOSARIO)


@APP.route("/informe")
def informe():
    cap_dir = None
    ult = globals().get("ULTIMA_CAPTURA")
    if ult and (EVID / ult).exists():
        cap_dir = EVID / ult
    elif CAPTURAS.exists():
        dirs = [d for d in CAPTURAS.iterdir() if d.is_dir()]
        cap_dir = max(dirs, key=lambda d: d.stat().st_mtime) if dirs else None

    resumen = None
    reporte_md = ""
    if cap_dir and (cap_dir / "resumen.json").exists():
        resumen = json.loads((cap_dir / "resumen.json").read_text())
        if (cap_dir / "reporte.md").exists():
            reporte_md = (cap_dir / "reporte.md").read_text(encoding="utf-8")
    if resumen is None:                       # sin captura: usa la corrida en vivo
        resumen = {
            "ts_label": datetime.now(timezone(timedelta(hours=-5))).strftime("%Y-%m-%d %H:%M:%S -05"),
            "iso": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "iso_local": "en vivo",
            "intervalo": (leer_estado_disco().get("mqtt", {}) or {}).get("intervalo", "?"),
            "nota": "sin captura: métricas del log en vivo",
            "protocolos": {p: metricas_completas(LOG_LIVE[p], LAT_KEY[p]) for p in PROTOS},
        }
        resumen["protocolos"]["coap_gw"] = metricas_completas(LOG_GW, "forward_latency_ms")
    return render_template("informe.html", cap=resumen, meta=DIDACTICA, info=APP_INFO,
                           carpeta=(cap_dir.name if cap_dir else None),
                           reporte_md=reporte_md,
                           pngs=(sorted(p.name for p in cap_dir.glob("*.png"))
                                 if cap_dir else []))


ARRANQUE = time.time()

if WATCHDOG:                       # un solo worker lo ejecuta de verdad (flock dentro)
    threading.Thread(target=vigilante, name="vigilante", daemon=True).start()

if __name__ == "__main__":
    puerto = int(os.environ.get("DASH_PORT", "8080"))
    print(f"[dashboard] http://0.0.0.0:{puerto}  (base={BASE})", flush=True)
    APP.run(host="0.0.0.0", port=puerto, threaded=True, debug=False)
