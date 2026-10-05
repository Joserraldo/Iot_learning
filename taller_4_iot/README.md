# Taller 4 — Laboratorio 4: AMQP + CoAP vs MQTT hacia Azure IoT Central

**UNAB · IoT + Cloud + Sistemas Distribuidos · `clima-salones-app-jose`**

Comparación experimental de **tres protocolos** publicando la misma telemetría
(`Temperature`, `Humidity`, `Iluminance`) hacia Azure IoT Central:

| # | Protocolo | Transporte | Puerto | Destino | Rol |
|---|-----------|-----------|--------|---------|-----|
| 1 | **MQTT** (baseline Lab 3) | TCP/TLS | 8883 | IoT Central directo | Línea base |
| 2 | **AMQP** | TCP/TLS (AMQP 1.0) | 5671 | IoT Central directo | Transmisión del plano de servicio Azure |
| 3 | **CoAP** | UDP | 5683 | Gateway propio (VM) → Central | Dispositivo constrained (no nativo de Central) |

## Arquitectura

```text
                        ┌──────────────────────────────┐
                        │       Azure IoT Central      │
                        │   clima-salones-app-jose     │
                        └───────┬──────────┬───────────┘
                                │          │
                    MQTT 8883  │          │ AMQP 5671
                                │          │
                        ┌───────▼──┐  ┌────▼──────────┐
                        │ device   │  │ device        │
                        │ 23z8rpgm │  │ amqp-lab4-01  │
                        └──────────┘  └───────────────┘
                                        (VM)
                                ▲
                                │ puente (MQTT/SDK)
                        ┌───────┴────────┐
                        │ coap_gateway   │  servidor CoAP UDP 5683 (VM)
                        └───────▲────────┘
                                │ CoAP UDP 5683
                        ┌───────┴────────┐
                        │ coap_client    │  nodo constrained (VM)
                        └────────────────┘
```

> **Nota CoAP:** CoAP no es nativo de IoT Central. El `coap_gateway` es el
> componente intermedio que recibe los datagramas CoAP (UDP/5683) y los reenvía
> a Central con el device `coap-gateway-01`. No se finge una conexión directa.

## Estructura

```
taller_4_iot/
├── README.md
├── laboratorio4.md            # especificación del lab
├── requirements.txt
├── .env.example / .gitignore
├── docs/bitacora.md           # bitácora continua
├── python/
│   ├── common.py              # generación compartida de las 3 variables
│   ├── amqp_sdk.py            # AMQP → IoT Central (transporte Amqp)
│   ├── coap_client.py         # nodo constrained CoAP
│   ├── coap_gateway.py        # servidor CoAP + puente a Central
│   └── provision_devices.py   # crea devices vía REST (tokens SAS)
├── evidencias/
│   ├── vm_azure_policy_hallazgo.md
│   ├── amqp/  coap/  comparativa/
│   └── capturas/              # evidencia capturada desde el dashboard
├── dashboard/                 # sala de control en vivo (Flask, corre en la VM)
│   ├── dashboard.py           # API + vistas (estado, start/stop, captura de evidencia)
│   ├── hacer_graficas.py      # PNG de cada captura (matplotlib/Agg)
│   └── templates/             # index.html (control room) · informe.html · _diagrama.html
└── tools/
    ├── vm_push.py  vm_pull.py  vmexec.py
    ├── dash_deploy.py         # sube + instala dependencias + reinicia el servicio systemd
    └── vm_https.py            # nginx + certificado Let's Encrypt para el dominio (una vez)
```

## Sala de control en vivo (dashboard)

**https://iotcentraljose.duckdns.org** — muestra los 3 protocolos publicando en vivo
(contador, latencia última/prom/mín/máx, payload, sparkline y la salida cruda de cada
script), permite **iniciar/detener** cada protocolo desde la página y tiene un apartado de
**evidencia** que congela la corrida (jsonl + stdout + `reporte.md` + 4 gráficas PNG) para
pegarla en el informe; también hay una página imprimible en `/informe` y descarga en
`/api/paquete.zip`. Las acciones de escritura piden la clave `DASH_KEY` del `.env`.

Además de las tarjetas y la comparativa, tiene una sección **🔬 Cómo viaja el mensaje** pensada
para entender los protocolos de un vistazo: **carrera de latencia** (un punto por mensaje real),
**pila de protocolos** de cada uno (aplicación/sesión/transporte/seguridad/red), **peso del
mensaje** (60 B de datos frente a la cabecera fija: MQTT 2 B, AMQP 8 B, CoAP 4 B), **secuencia
real del último intercambio** con los tiempos medidos, *qué mide cada KPI*, *cuándo usar cada
protocolo* y un **glosario** de los términos (QoS 1, CBS, disposition, CON/2.04, gateway…).

### Despliegue

```bash
python tools/dash_deploy.py    # sube dashboard/, instala flask/matplotlib/gunicorn y reinicia
python tools/vm_https.py       # (una sola vez) nginx + certificado Let's Encrypt
```

Infraestructura en la VM: **nginx** (puertos 80/443, TLS de Let's Encrypt, redirect 80→443) →
**gunicorn** en `127.0.0.1:8080` como servicio systemd `taller4-dashboard`. El puerto 8080 no
está expuesto: la única entrada pública es nginx por HTTPS.

```bash
sudo systemctl status taller4-dashboard     # estado del dashboard
journalctl -u taller4-dashboard -n 50       # logs
sudo systemctl reload nginx                 # recargar nginx
sudo certbot certificates                   # estado del certificado
python tools/vm_robustez.py                 # swap + límites de log (una vez; idempotente)
python tools/vm_https.py --dry-run          # probar la renovación del certificado
```

### Robustez (pensada para aguantar meses de demos)

- **Vigilante interno:** si un cliente se cae o se pasa de 260 MB, el dashboard lo relanza solo
  sin borrar el log (la corrida continúa) y lo registra en `evidencias/autoreinicio.log`.
- **Rotación automática** de los `live*.jsonl` al pasar 40 MB.
- **Servidor:** swap de 2 GB, journald limitado a 200 MB, `MemoryMax=450M` para el servicio.
- **Consumo real medido:** dashboard ≈ 111 MB, cada cliente 20–42 MB, disco +~25 MB/día (23 GB
  libres), CPU ~5 %. Alcanza de sobra hasta diciembre.
- **Reinicio de la VM probado:** vuelve en ~20 s y todo arranca solo (nginx, dashboard y los 3
  protocolos vía vigilante, con los contadores continuando). Un redespliegue del dashboard no corta
  la corrida en curso (`KillMode=process`).
- **Riesgo externo:** si la VM se *desasigna* en Azure, la IP pública puede cambiar y DuckDNS
  quedaría apuntando mal; y DuckDNS borra el subdominio tras ~30 días sin actualizar (conviene
  un cron diario con el token).

## Seguridad

- Credenciales **solo** por variables de entorno (`.env`, no versionado).
- Tokens SAS y primary keys **nunca** se imprimen, loguean ni commitean.
- Los devices se crean vía REST con token admin; las keys van al `.env` de la VM.

## Cómo reproducir (en la VM)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env .env   # pegar credenciales reales
python python/provision_devices.py        # crear devices (1ra vez)
python python/amqp_sdk.py                 # AMQP → Central
python python/coap_gateway.py &           # gateway CoAP (en VM)
python python/coap_client.py              # nodo CoAP → gateway → Central
```

Corridas en vivo continuas (lo que consume el dashboard, sobrevive al cierre de SSH):

```bash
cd ~/taller_4_iot
setsid nohup .venv/bin/python -u python/mqtt_baseline.py --duration 0 --interval 3 --log evidencias/mqtt/live.jsonl > evidencias/mqtt/live.log 2>&1 < /dev/null &
setsid nohup .venv/bin/python -u python/amqp_sdk.py      --duration 0 --interval 3 --log evidencias/amqp/live.jsonl > evidencias/amqp/live.log 2>&1 < /dev/null &
setsid nohup .venv/bin/python -u python/coap_gateway.py  --log evidencias/coap/live-gw.jsonl > evidencias/coap/live-gw.log 2>&1 < /dev/null &
sleep 3
setsid nohup .venv/bin/python -u python/coap_client.py   --duration 0 --interval 3 --log evidencias/coap/live-client.jsonl > evidencias/coap/live-client.log 2>&1 < /dev/null &
```

> Desde la página basta con **▶ Iniciar los 3** (o la corrida cronometrada de 90 s).
