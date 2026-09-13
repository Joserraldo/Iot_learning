# Taller 3: UNAB-Ambiental — Abrir la caja negra MQTT

## Propósito

Hacer visible el protocolo MQTT que el SDK de Azure ocultó en el Laboratorio 2:
documentar qué hay detrás de `IoTHubDeviceClient.create_from_connection_string()`
y `send_telemetry_message()` (conexión, autenticación, pub/sub), y construir un
cliente MQTT **explícito** con `paho-mqtt` que hable directamente con el hub de
IoT Central — sin SDK — publicando telemetría PnP y manejando twin/commands.

## Etapas (guía UNAB-Ambiental)

1. **Etapa 1 — Abrir la caja negra**: documentar el MQTT oculto (hostname del hub asignado por DPS, puerto 8883/TLS, formato del payload JSON,username/password MQTT, temas).
2. **Etapa 2 — Cliente MQTT explícito** (`mqtt_explicito.py`, paho-mqtt): SAS token HMAC-SHA256 en memoria, conexión TLS al hub, publicación de `Temperature`/`Humidity`/`Iluminance`, suscripción a twin desired-properties y methods.
3. **Etapa 3 — Mediciones**: tamaño de payload, intervalos reales, latencia publish→ack, QoS 0/1/2, comportamiento ante cortes de red y reconexión.
4. **Etapa 4 — Comparación y conclusión**: SDK vs MQTT explícito vs Wokwi/Arduino; qué conviene para UNAB-Ambiental.

## Componentes previstos

- `mqtt_explicito.py` — cliente MQTT explícito (sin `azure-iot-device`).
- `requirements.txt` — dependencias (solo `paho-mqtt`).
- `docs/bitacora.md` — bitácora del laboratorio.
- `evidencias/` — logs, capturas y tablas de mediciones.
- `.env` (local, NO versionado) — credenciales vía variables de entorno.

## Relación con el Laboratorio 2

Este laboratorio **complementa** sin modificar el código del Lab 2: reutiliza
la plantilla `consola-unab-ambiental` (telemetría `Temperature`/`Humidity`/`Iluminance`,
property writable `Set_temp_hvac`, comandos `Encender_hvac`/`force_reading`) y el
mismo hub al que DPS asignó los dispositivos.

## Seguridad

- Credenciales **solo** por variables de entorno (ver `.env.example`).
- Keys y SAS tokens **nunca** se imprimen, loguean ni commitean; el SAS token se
  construye en memoria y expira.
- Nada de valores de `.env` en la bitácora ni en `evidencias/`.

## Documentación

- [Bitácora del taller](docs/bitacora.md)
