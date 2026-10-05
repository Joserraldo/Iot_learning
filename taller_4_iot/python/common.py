#!/usr/bin/env python3
"""
common.py — Generación compartida de telemetría para los 3 protocolos del Lab 4.

Misma lógica de random-walk que python-vm-01.py (Lab 2) y mqtt_explicito.py
(Lab 3): las 3 variables son Temperature, Humidity y Iluminance, con la misma
plantilla DTDL consola-unab-ambiental, para que la comparación entre protocolos
sea equivalente (mismos rangos, mismo formato JSON plano de 1 decimal).
"""

import json
import os
import random
import time
import base64
import hashlib
import hmac
from urllib.parse import quote_plus

# Estado inicial (idéntico al Lab 2/3)
_state = {"Temperature": 24.0, "Humidity": 50.0, "Iluminance": 400.0}

# Rangos físicos de la plantilla DTDL (Lab 2)
LIMITS = {
    "Temperature": (16.0, 32.0),
    "Humidity": (35.0, 70.0),
    "Iluminance": (100.0, 800.0),
}


def generar_lectura() -> dict:
    """Random-walk ±0.5 por variable, respetando rangos de la plantilla."""
    for k, (lo, hi) in LIMITS.items():
        delta = random.uniform(-0.5, 0.5)
        _state[k] = round(min(hi, max(lo, _state[k] + delta)), 1)
    return dict(_state)


def payload_json() -> tuple[str, int]:
    """Devuelve (payload_str, bytes_utf8) con el JSON plano de 3 variables."""
    s = json.dumps(generar_lectura())
    return s, len(s.encode("utf-8"))


def ahora_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


DPS_HOST = "global.azure-devices-provisioning.net"


def build_sas_token(hostname: str, device_id: str, primary_key_b64: str, ttl: int = 3600) -> str:
    """SharedAccessSignature sr={resource}&sig={sig}&se={exp} — misma fórmula
    verificada en el Lab 3 (mqtt_explicito.py). Se construye SOLO en memoria.
    Compartida por mqtt_baseline.py y amqp_sdk.py (MQTT y AMQP usan el mismo
    token SAS contra el mismo resource {hub}/devices/{id})."""
    resource = quote_plus(f"{hostname}/devices/{device_id}")
    expiry = int(time.time() + ttl)
    signing_key = base64.b64decode(primary_key_b64)
    digest = hmac.new(
        signing_key, f"{resource}\n{expiry}".encode("utf-8"), hashlib.sha256
    ).digest()
    sig = quote_plus(base64.b64encode(digest).decode("utf-8"))
    return f"SharedAccessSignature sr={resource}&sig={sig}&se={expiry}"
DPS_CACHE_FILE = ".dps_cache.json"  # conn strings resueltos (device_id -> cs); NO versionar


def _cache_get(device_id: str) -> str | None:
    try:
        with open(DPS_CACHE_FILE, encoding="utf-8") as f:
            return json.load(f).get(device_id)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _cache_put(device_id: str, conn_str: str) -> None:
    try:
        data = {}
        with open(DPS_CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    data[device_id] = conn_str
    with open(DPS_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def central_conn_str(device_id: str, device_key: str, id_scope: str | None = None,
                     retries: int = 4) -> str:
    """Registro DPS (idempotente) y connection string con el hub asignado REAL.

    La app fue recreada: el hostname del hub cambió respecto al Lab 3, así que
    no se confía en el .env — DPS devuelve el hub vigente para el idScope dado.
    Cachea el resultado en .dps_cache.json para no golpear DPS en cada corrida
    (el throttling de DPS ante registros repetidos produce 'Unexpected failure').
    """
    from azure.iot.device import ProvisioningDeviceClient

    cached = _cache_get(device_id)
    if cached:
        print(f"[DPS] {device_id} -> conn string de cache (sin registro)")
        return cached

    id_scope = id_scope or os.environ["ID_SCOPE"]
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            client = ProvisioningDeviceClient.create_from_symmetric_key(
                provisioning_host=DPS_HOST,
                registration_id=device_id,
                id_scope=id_scope,
                symmetric_key=device_key,
            )
            result = client.register()
            hub = result.registration_state.assigned_hub
            conn_str = f"HostName={hub};DeviceId={device_id};SharedAccessKey={device_key}"
            print(f"[DPS] {device_id} -> assigned_hub={hub}")
            _cache_put(device_id, conn_str)
            return conn_str
        except Exception as e:  # noqa: BLE001 — DPS es intermitente (throttle)
            last_err = e
            wait = 3 * attempt
            print(f"[DPS] intento {attempt}/{retries} falló ({type(e).__name__}), "
                  f"reintento en {wait}s")
            time.sleep(wait)
    raise last_err  # type: ignore[misc]


if __name__ == "__main__":
    p, n = payload_json()
    print(p, f"({n} bytes)")
