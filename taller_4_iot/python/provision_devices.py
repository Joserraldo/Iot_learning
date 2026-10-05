#!/usr/bin/env python3
"""
provision_devices.py — Crea dispositivos dedicados en Azure IoT Central vía REST
y escribe sus primary keys en el .env (AMQP_DEVICE_PRIMARY_KEY, COAP_DEVICE_PRIMARY_KEY).

Usa la REST API de IoT Central (api-version=2022-07-31) autenticando con el
token SAS de la app (admin) que debe estar en el .env como IOT_CENTRAL_TOKEN_ADMIN.

Para cada device:
  1. Crea el device asociado a la plantilla consola-unab-ambiental.
  2. Lee sus credenciales (symmetric key) para armar el connection string.
  3. Actualiza el .env (no versionado) con la primary key obtenida.

El token SAS y las primary keys NUNCA se imprimen en claro.

Uso:
  python python/provision_devices.py            # lee .env
  python python/provision_devices.py --list     # solo lista plantillas/devices
"""

import os
import re
import sys
import json
import argparse
import logging
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv, set_key

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PROVISION] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

API_VERSION = "2022-07-31"

DEVICES = [
    {"id": "mqtt-baseline-01", "label": "MQTT baseline (Lab 3)", "env_key": "MQTT_DEVICE_PRIMARY_KEY"},
    {"id": "amqp-lab4-01", "label": "AMQP (Lab 4)", "env_key": "AMQP_DEVICE_PRIMARY_KEY"},
    {"id": "coap-gateway-01", "label": "CoAP gateway (Lab 4)", "env_key": "COAP_DEVICE_PRIMARY_KEY"},
]


def api(base: str, token: str, path: str, method: str = "GET", body=None) -> requests.Response:
    # La REST API de IoT Central exige el prefijo /api/ en el path.
    if not path.startswith("/api/"):
        path = "/api" + path
    url = f"https://{base}{path}"
    headers = {"Authorization": token, "Content-Type": "application/json"}
    r = requests.request(method, url, headers=headers, json=body, timeout=40)
    return r


def find_template_id(base: str, token: str) -> str | None:
    """Devuelve el id de la plantilla asociada al device MQTT del Lab 3 (23z8rpgm6s4)
    o el que contenga 'consola'/'ambiental' en su displayName."""
    r = api(base, token, f"/deviceTemplates?api-version={API_VERSION}")
    if r.status_code != 200:
        logger.error(f"GET /deviceTemplates -> {r.status_code} {r.text[:200]}")
        return None
    for t in r.json().get("value", []):
        name = t.get("displayName", "") or ""
        tid = t.get("@id") or t.get("id")
        if "consola" in name.lower() or "ambiental" in name.lower():
            return tid
    return None


def get_template_id_from_device(base: str, token: str, device_id: str) -> str | None:
    r = api(base, token, f"/devices/{quote_plus(device_id)}?api-version={API_VERSION}")
    if r.status_code != 200:
        logger.error(f"GET /devices/{device_id} -> {r.status_code} {r.text[:200]}")
        return None
    return r.json().get("template")


def create_device(base: str, token: str, device_id: str, template_id: str) -> bool:
    body = {
        "displayName": device_id,
        "simulated": False,
        "enabled": True,
        "template": template_id,
    }
    r = api(base, token, f"/devices/{quote_plus(device_id)}?api-version={API_VERSION}",
            method="PUT", body=body)
    if r.status_code not in (200, 201):
        logger.error(f"PUT /devices/{device_id} -> {r.status_code} {r.text[:300]}")
        return False
    logger.info(f"Device {device_id} creado/actualizado OK")
    return True


def get_device_key(base: str, token: str, device_id: str) -> str | None:
    r = api(base, token, f"/devices/{quote_plus(device_id)}/credentials?api-version={API_VERSION}")
    if r.status_code != 200:
        logger.error(f"GET credenciales {device_id} -> {r.status_code} {r.text[:200]}")
        return None
    data = r.json()
    if "symmetricKey" in data and data["symmetricKey"].get("primaryKey"):
        return data["symmetricKey"]["primaryKey"]
    for cred in data.get("credentials", []):
        if cred.get("type") == "symmetricKey":
            return cred["symmetricKey"]["primaryKey"]
    return None


def redact(s: str) -> str:
    return (s[:6] + "…" + s[-4:]) if s else "(vacío)"


def ensure_template(base: str, token: str, template_id: str) -> bool:
    """Crea la plantilla consola-unab-ambiental si no existe (el Lab 3 la tenía
    pero la app fue recreada y perdió la plantilla original). Idempotente."""
    r = api(base, token, f"/deviceTemplates/{quote_plus(template_id)}?api-version={API_VERSION}")
    if r.status_code == 200:
        logger.info(f"Plantilla ya existe: {template_id}")
        return True
    body = {
        "@type": ["ModelDefinition", "DeviceModel"],
        "@id": template_id,
        "displayName": "consola-unab-ambiental",
        "capabilityModel": {
            "@id": "dtmi:unabAmbientalJose:consolaUnabAmbiental;1",
            "@type": "Interface",
            "displayName": "consola-unab-ambiental",
            "contents": [
                {"@type": "Telemetry", "name": "Temperature",
                 "displayName": "Temperature", "schema": "double",
                 "unit": "degreeCelsius"},
                {"@type": "Telemetry", "name": "Humidity",
                 "displayName": "Humidity", "schema": "double",
                 "unit": "percent"},
                {"@type": "Telemetry", "name": "Iluminance",
                 "displayName": "Iluminance", "schema": "double",
                 "unit": "lux"},
            ],
        },
    }
    r = api(base, token, f"/deviceTemplates/{quote_plus(template_id)}?api-version={API_VERSION}",
            method="PUT", body=body)
    if r.status_code in (200, 201):
        logger.info(f"Plantilla {template_id} creada OK")
        return True
    logger.error(f"PUT plantilla -> {r.status_code} {r.text[:300]}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Crea devices dedicados en IoT Central")
    parser.add_argument("--list", action="store_true", help="solo listar plantillas/devices")
    parser.add_argument("--env", default=".env", help="ruta al .env")
    args = parser.parse_args()

    load_dotenv(args.env)
    base = os.getenv("IOT_CENTRAL_APP")
    token = os.getenv("IOT_CENTRAL_TOKEN_ADMIN")
    if not base or not token:
        logger.error("Faltan IOT_CENTRAL_APP o IOT_CENTRAL_TOKEN_ADMIN en .env")
        sys.exit(1)

    if args.list:
        r = api(base, token, f"/deviceTemplates?api-version={API_VERSION}")
        print("Plantillas:", r.status_code)
        for t in r.json().get("value", []):
            print(" -", t.get("@id") or t.get("id"), "|", t.get("displayName"))
        r = api(base, token, f"/devices?api-version={API_VERSION}")
        print("Devices:", r.status_code)
        for d in r.json().get("value", []):
            print(" -", d.get("id"), "| template:", d.get("template"))
        return

    template_id = os.getenv("MODEL_ID") or "dtmi:unabAmbientalJose:consolaUnabAmbiental_1pu;1"
    if not get_template_id_from_device(base, token, os.getenv("MQTT_DEVICE_ID", "23z8rpgm6s4")):
        logger.info("Device MQTT del Lab 3 no encontrado; se usará MODEL_ID del .env")
    if not ensure_template(base, token, template_id):
        sys.exit(1)
    logger.info(f"Plantilla asegurada: {template_id}")

    for dev in DEVICES:
        device_id = dev["id"]
        logger.info(f"=== {dev['label']} ({device_id}) ===")
        if not create_device(base, token, device_id, template_id):
            continue
        key = get_device_key(base, token, device_id)
        if not key:
            logger.warning(f"No se pudo leer la key de {device_id}")
            continue
        logger.info(f"Primary key {device_id}: {redact(key)} (en .env)")
        set_key(args.env, dev["env_key"], key)

    logger.info("Listo. Las primary keys quedaron en el .env local.")


if __name__ == "__main__":
    main()
