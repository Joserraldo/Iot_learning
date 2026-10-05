# IoT Learning — UNAB

Repositorio de trabajos, laboratorios y evidencias de la asignatura **Internet de
las Cosas (IoT) + Cloud + Sistemas Distribuidos**. El proyecto documenta una
solución IoT completa: generación de telemetría, dispositivos simulados, conexión
segura con Azure IoT Central, ejecución de nodos en una VM, control remoto,
medición de protocolos y análisis de resultados.

> **Estado:** laboratorios 1 a 4 desarrollados. Cada carpeta contiene su código,
> instrucciones, bitácora y, cuando aplica, informes y evidencias de ejecución.

## Recorrido del curso

| Taller | Tema principal | Resultado |
| --- | --- | --- |
| [Taller 1](taller_1_iot/) | Introducción al problema ambiental y diseño de la solución IoT | Material de laboratorio e informes en PDF |
| [Taller 2](taller_2_iot/) | Sistema IoT conectado a Azure IoT Central | Nodo Python en VM, dashboard Flask y ESP32 simulado con Wokwi |
| [Taller 3](taller_3_iot/) | MQTT explícito: abrir la caja negra del SDK de Azure | Cliente `paho-mqtt`, DPS, SAS, gemelo, comandos y mediciones de QoS |
| [Taller 4](taller_4_iot/) | Comparación de MQTT, AMQP y CoAP | Tres clientes, gateway CoAP, dashboard de control y comparación experimental |

La solución usa como modelo de datos común la plantilla
`consola-unab-ambiental`, con las variables de telemetría:
`Temperature`, `Humidity` e `Iluminance`.

## Arquitectura general

```text
┌──────────────────────┐       MQTT/TLS       ┌──────────────────────────┐
│ ESP32 simulado       │ ────────────────────► │                          │
│ Wokwi + DHT22       │                       │                          │
└──────────────────────┘                       │   Azure IoT Central      │
                                               │   DPS + IoT Hub           │
┌──────────────────────┐   MQTT/TLS / AMQP   │   Telemetría, gemelo,     │
│ VM de Azure          │ ───────────────────► │   propiedades y comandos   │
│ nodos Python         │                       │                          │
└──────────┬───────────┘                       └──────────────────────────┘
           │
           │ CoAP/UDP
           ▼
┌──────────────────────┐
│ Gateway CoAP         │ ── puente MQTT/TLS ──► Azure IoT Central
└──────────────────────┘
```

### Capacidades implementadas

- Provisionamiento y asignación de dispositivos mediante **Azure Device
  Provisioning Service (DPS)**.
- Autenticación con **SAS tokens HMAC-SHA256** generados en memoria.
- Telemetría periódica de temperatura, humedad e iluminación.
- Propiedades reportadas y deseadas del gemelo digital.
- Comandos cloud-to-device, incluido `force_reading` y el control del LED/HVAC.
- Dashboard Flask para consultar el estado, visualizar lecturas y controlar el
  sistema.
- Simulación de ESP32 con DHT22, potenciómetro y LED en Wokwi.
- Cliente MQTT explícito con pruebas de QoS, latencia, reconexión y cortes de red.
- Cliente AMQP 1.0 explícito con `uamqp`.
- Gateway CoAP sobre UDP que traduce mensajes a MQTT para IoT Central.
- Captura de logs JSONL, métricas y gráficas comparativas.

## Estructura del repositorio

```text
Iot_learning/
├── README.md
├── taller_1_iot/                 # Introducción, guías e informes en PDF
├── taller_2_iot/                 # Azure IoT Central + VM + Wokwi
│   ├── python-vm-01.py
│   ├── wokwi/
│   ├── docs/
│   └── tools/
├── taller_3_iot/                 # MQTT explícito y medición de QoS
│   ├── mqtt_explicito.py
│   ├── evidencias/
│   └── docs/
└── taller_4_iot/                 # AMQP + CoAP vs MQTT
    ├── python/
    ├── dashboard/
    ├── evidencias/
    └── tools/
```

Los archivos `README.md` de cada taller son la referencia operativa de su
respectiva práctica:

- [Taller 2 — Sistema IoT en Azure](taller_2_iot/README.md)
- [Taller 3 — MQTT explícito](taller_3_iot/README.md)
- [Taller 4 — AMQP + CoAP vs MQTT](taller_4_iot/README.md)

Las bitácoras explican decisiones, problemas encontrados y verificaciones:
[Taller 2](taller_2_iot/docs/bitacora.md), [Taller 3](taller_3_iot/docs/bitacora.md)
y [Taller 4](taller_4_iot/docs/bitacora.md).

## Tecnologías y protocolos

| Capa | Tecnologías |
| --- | --- |
| Dispositivo | ESP32, Arduino, Wokwi, DHT22, potenciómetro y LED |
| Aplicación | Python 3, Flask, `python-dotenv` |
| IoT y nube | Azure IoT Central, DPS, IoT Hub y Azure VM |
| Mensajería | MQTT 3.1.1, AMQP 1.0 y CoAP (RFC 7252) |
| Seguridad | TLS, SAS y HMAC-SHA256 |
| Observabilidad | Logs JSONL, métricas de latencia, gráficas y dashboard |

### Hallazgos técnicos destacados

- El SDK Python de Azure abstrae MQTT: el transporte usa MQTT 3.1.1 sobre TLS,
  normalmente por el puerto 8883, con autenticación SAS.
- El cliente MQTT explícito permite observar topics, payloads, PUBACK, QoS y
  reconexiones que el SDK oculta.
- `azure-iot-device` 2.x no incluye transporte AMQP; por eso el laboratorio 4
  usa `uamqp` para probar AMQP 1.0 directamente.
- CoAP no es nativo de IoT Central en esta solución. Por eso se implementa un
  gateway que recibe UDP/5683 y reenvía la telemetría mediante MQTT/TLS.
- MQTT es el camino más directo para dispositivos; AMQP resulta apropiado para
  mensajería con garantías y sesiones; CoAP es útil en el borde, pero requiere
  gateway para integrarse con IoT Central.

## Requisitos

- Python 3.12 o superior recomendado.
- Una cuenta y recursos de Azure IoT Central para ejecutar los talleres 2 a 4.
- Una VM Linux en Azure para los nodos y pruebas formales de los laboratorios.
- VS Code.
- Para el taller 2: extensión **Wokwi for VS Code**, Arduino CLI y core ESP32.
- Conectividad saliente a:
  - DPS: `global.azure-devices-provisioning.net:8883`
  - IoT Hub: puerto MQTT `8883` o AMQP `5671`, según la prueba.

Cada taller declara sus propias dependencias en un `requirements.txt`. No se
deben usar ni versionar los entornos `.venv`; deben crearse localmente.

## Preparación de un taller Python

Desde la carpeta del taller que se desea ejecutar:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

En Linux o dentro de la VM:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Los talleres que requieren configuración incluyen `.env.example`. Se debe copiar
como `.env` y completar los valores desde Azure IoT Central:

```powershell
Copy-Item .env.example .env
```

Nunca se deben subir al repositorio archivos `.env`, claves primarias, tokens SAS,
certificados ni credenciales SSH. Los `.gitignore` de los talleres excluyen estos
archivos y los artefactos generados.

## Ejecución rápida por taller

### Taller 2

Consulta primero la [guía de la VM](taller_2_iot/docs/guia-vm-azure.md) y el
[README del taller](taller_2_iot/README.md). El nodo principal es
[`python-vm-01.py`](taller_2_iot/python-vm-01.py); el proyecto ESP32 se ejecuta
desde [taller_2_iot/wokwi](taller_2_iot/wokwi/).

```bash
cd taller_2_iot
python python-vm-01.py
```

El dashboard Flask queda disponible localmente en el puerto 5000. Si el puerto
no está publicado por el firewall de Azure, se puede usar un túnel SSH:

```bash
ssh -L 5000:localhost:5000 usuario@IP_DE_LA_VM
```

### Taller 3

Este taller reutiliza la misma plantilla de IoT Central, pero reemplaza el SDK
por `paho-mqtt` para observar el protocolo directamente:

```bash
cd taller_3_iot
python mqtt_explicito.py
```

Las mediciones y conclusiones están en [`informe-lab3.md`](taller_3_iot/informe-lab3.md)
y los datos crudos en [`evidencias/`](taller_3_iot/evidencias/).

### Taller 4

El [README del taller 4](taller_4_iot/README.md) contiene la arquitectura, el
despliegue del dashboard y los comandos completos. Sus clientes principales son:

```bash
cd taller_4_iot
python python/provision_devices.py   # solo la primera vez
python python/mqtt_baseline.py
python python/amqp_sdk.py
python python/coap_gateway.py        # dejar ejecutándose
python python/coap_client.py
```

La comparación formal usa corridas controladas y evidencia en
[`taller_4_iot/evidencias/`](taller_4_iot/evidencias/). El informe resume
latencia, tamaño de payload, confiabilidad, handshake y casos de uso de cada
protocolo.

## Reproducibilidad y evidencias

Las evidencias se organizan junto al taller que las produjo:

- Bitácoras cronológicas en `docs/bitacora.md`.
- Informes de laboratorio en Markdown y PDF.
- Logs de ejecución y mediciones en JSONL.
- Gráficas comparativas en `evidencias/comparativa/`.
- Diagramas y capturas de la arquitectura y del dashboard.

Para repetir una medición, se recomienda registrar el dispositivo utilizado, el
intervalo, el protocolo, el QoS, la duración de la corrida y las condiciones de
red. Así los resultados pueden compararse sin mezclar telemetría entre devices.

## Seguridad y buenas prácticas

- Mantener secretos únicamente en variables de entorno o en el gestor de
  secretos de la VM.
- No imprimir claves, tokens SAS ni valores completos de `.env` en logs,
  bitácoras, capturas o informes.
- Usar un dispositivo distinto por protocolo para evitar colisiones de identidad
  y mezclar telemetría.
- Preferir túneles SSH o HTTPS para dashboards; no exponer puertos de desarrollo
  innecesariamente.
- Revisar los logs antes de compartir evidencias públicamente.
- Eliminar o rotar credenciales de Azure cuando una práctica termine.

## Estado y próximos pasos

El repositorio ya cubre la cadena principal de aprendizaje: dispositivo,
protocolo, nube, operación y medición. Como continuación natural se pueden
agregar nuevos talleres manteniendo la misma convención:

1. Crear una carpeta `taller_N_iot/`.
2. Añadir un README con objetivo, arquitectura, requisitos, ejecución y resultado.
3. Separar código fuente, documentación, evidencias y herramientas operativas.
4. Incluir un `requirements.txt` y `.env.example` sin secretos.
5. Registrar las pruebas y decisiones en `docs/bitacora.md`.

## Autoría

Trabajo académico de **José Alejandro Téllez Prada** para la asignatura de IoT,
Cloud y Sistemas Distribuidos — UNAB.
