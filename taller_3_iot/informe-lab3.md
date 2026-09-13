# Laboratorio 3 — MQTT hacia Azure IoT Central
**UNAB · IoT + Cloud + Sistemas Distribuidos · UNAB-Ambiental**
José Tellez · App: `unab-ambiental-jose.azureiotcentral.com` · VM Ubuntu (Azure) + Wokwi ESP32
Re-ejecución formal: 2026-09-13 19:50–20:19 UTC (VM encendida, reloj NTP sincronizado al momento de las mediciones)

## 1. Objetivos cumplidos
1. Explicar qué protocolo usa realmente un dispositivo hacia IoT Central: **MQTT 3.1.1 sobre TLS (puerto 8883), con autenticación SAS (HMAC-SHA256), pasando primero por DPS y luego por el IoT Hub subyacente de la app**.
2. Publicar las mismas 3 variables del Lab 2 (`Temperature`, `Humidity`, `Iluminance`) por dos caminos: **SDK Python** (baseline, `python-vm-01.py`) y **cliente MQTT explícito** (`mqtt_explicito.py`, paho puro, sin `azure-iot-device`).
3. Mantener el ESP32 de Wokwi (firmware Arduino, mismo proyecto Lab 2) enviando por MQTT/TLS a la misma aplicación.
4. Medir tamaño de payload, intervalo, latencia y comportamiento ante corte y ante QoS 0/1/2.

## 2. Flujo real (evidencia: `evidencias/miapp-2026-09-13/dps-manual-y-telemetria.log`)

```
 Dispositivo (VM/Wokwi)                        DPS                          IoT Hub de la app           IoT Central
        │  1 TLS 8883  mqtts://global.azure-devices-provisioning.net          │                              │
        ├─ username: {id-scope}/registrations/{device-id}/?api-version=…      │                              │
        ├─ password: SharedAccessSignature(HMAC-SHA256)                       │                              │
        │  2 PUT $dps/registrations/PUT/iotdps-register/?$rid=1               │                              │
        │◄─ 202 status=assigning (retry-after=3) ─────────────────────────────┤                              │
        │  3 GET …iotdps-get-operationstatus?operationId=…                    │                              │
        │◄─ 200 status=assigned  assignedHub=iotc-47a415d3-….net ─────────────┤                              │
        │  4 CONNACK TLS 8883 a ese hub (username=hub/device/?api-version=2019-10-01, pw=SAS)                 │
        │  5 PUBLISH devices/23z8rpgm6s4/messages/events/  {Temperature,…} ───►│── ingestión ────────────────►│ Data explorer
        │◄─ PUBACK (QoS 1) ───────────────────────────────────────────────────┤                              │
```
Detalles verificados "a mano": el subdominio `{id-scope}.global…` no resuelve (hay que ir a `global.azure-devices-provisioning.net` y llevar el scope en el username); tras `assigning` corresponde GET de operación, no re-PUT (re-PUTs producen `409 / 409203 Precondition failed`).

## 3. Tabla de mediciones (cliente explícito, device `23z8rpgm6s4`)

| Concepto | Valor medido | Evidencia |
|---|---|---|
| Tamaño payload (3 variables) | **60 bytes** UTF-8 `{"Temperature": …, "Humidity": …, "Iluminance": …}` (1 decimal) | `qos1.jsonl` (bytes por mensaje) |
| Topic de telemetría | `devices/23z8rpgm6s4/messages/events/` | todos los logs |
| Intervalo configurado vs observado | 10 s vs **10.0–10.1 s** (marcas `t_pub` del SUMMARY) | `qos1.jsonl` |
| Latencia publish → PUBACK (QoS 1) | **avg 230.6 ms** (mín 206.1, máx 333.9; n=6) | `qos1.log` SUMMARY |
| Latencia publish →_ack_ (QoS 0) | 0.3–0.4 ms = **ack LOCAL**, sin confirmación del broker | `qos0.log` |
| Latencia percibida hasta Central | public→PUBACK medido (≈231 ms); el tramo PUBACK→gráfico se valida visualmente en captura 15 (ingesta de Central, no medible desde el dispositivo) | portal |
| Corte de red a los 25 s (QoS 1) | socket cerrado → **reconexión automática con backoff** (2 conexiones) → 6/6 acks, **0 mensajes perdidos** | `corte.log` SUMMARY |
| QoS 0 | aceptado por Central (publica sin confirmación) | `qos0.log` |
| QoS 1 | aceptado; handshake PUBLISH→PUBACK normal | `qos1.log` |
| QoS 2 | PUBLISH QoS 2 aceptado, **pero el broker responde PUBACK** (6/6) y **nunca** envía PUBREC/PUBREL/PUBCOMP (0/6) → **degradado a QoS 1 en el alambre** | `qos2.log` con `--debug-packets` |

## 4. Comparación de los tres caminos (misma app, mismas 3 variables)

| Criterio | SDK Python (Lab 2) | MQTT explícito (paho) | Wokwi ESP32 (Arduino) |
|---|---|---|---|
| Facilidad | Alta (2 llamadas) | Media (SAS/topics/subscribe a mano) | Baja-media (SDK C + estado a mano) |
| Control/visibilidad del protocolo | Nula (es la "caja negra") | **Total** (paquetes, QoS, topics) | Parcial (logs del sketch) |
| Payload | 60 B | 60 B (idéntico, misma plantilla) | 60 B |
| Latencia publish→ack | no medía nada | **230.6 ms avg medida** | depende del navegador/Wokwi |
| Reconexión | automática del SDK | automática de paho (probada con corte) | manual: `WiFi.reconnect()` + máquina de estados |
| Utilidad para UNAB-Ambiental | operación diaria del nodo VM | **diagnóstico** (¿TLS? ¿SAS? ¿topic? ¿QoS?) | único camino en hardware real |

**Conclusión de QoS (pedida explícitamente):** IoT Central/IoT Hub admite **QoS 0 y 1 y no implementa QoS 2**: al pedirlo, la telemetría no falla pero el broker confirma con un simple PUBACK — es decir, la promesa MQTT de "exactamente una vez" **no existe** contra Central; elegir QoS 1 da "al menos una vez" con menor tráfico, y es lo que el SDK ya hace. Por eso el QoS 2 medido muestra RTT casi igual a QoS 1 (252.8 vs 230.6 ms): el paquete extra del handshake simplemente nunca ocurre.

**¿Cuándo SDK y cuándo MQTT desnudo?** SDK para el nodo operativo (reconexión probada, cero mantenimiento); cliente explícito como herramienta de diagnóstico y como puente si el proyecto migra algún día a un broker propio (Mosquitto en el salón), donde el código es reutilizable casi sin cambios.

## 5. Evidencias del repo
- Scripts: `mqtt_explicito.py` (explícito, oficial) y `mqtt-explicit-01.py` (demo DPS manual, en la VM), SDK Lab 2 intacto.
- Logs/capturas: `evidencias/miapp-2026-09-13/` (QoS 0/1/2 + paquetes crudos, corte, DPS manual) y bitácora con entrada VOID de la tanda anterior (credenciales ajenas ya retiradas).
- SAS sin secretos en claro: el token se genera en memoria desde `AZURE_PRIMARY_KEY` vía variables de entorno (`.env` fuera de git); nunca se imprime.
- Capturas portal 15-21: el SDK publica cada 10 s en vivo. **Nota C2D (captura 20):** IoT Central moderno retiró el envío cloud-to-device (no hay endpoint REST ni UI); la evidencia downlink real del laboratorio son los métodos directos (4x force_reading respondidos 200 por el cliente sin SDK) y el gemelo leido por MQTT puro; la suscripcion devicebound quedo concedida (SUBACK).
