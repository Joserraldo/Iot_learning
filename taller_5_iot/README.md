# Taller 5 — Plataforma propia: MQTT → InfluxDB → Grafana (+ alerta email)

Laboratorio 5 de IoT + Cloud + Sistemas Distribuidos (UNAB). Del todo gestionado
en Azure IoT Central de los talleres 1–4 pasamos a **nuestra propia plataforma**:
un broker, una base de datos de series de tiempo y un visualizador con alertas,
**todos corriendo dentro de la misma VM de Azure** con Docker Compose, servidos
bajo el mismo dominio `https://iotcentraljose.duckdns.org`.

```
publicador (python/publisher.py)            ┌─ didactico ─ https://iotcentraljose.duckdns.org/taller5/
   │  MQTT QoS1, topic lab5/telemetria      │
   ▼                                        │            └─ lectura con token SOLO-LECTURA (Flux)
mosquitto ──► ingestor (python/ingest.py) ──┤                    ▲
   (broker)        │  line protocol         │                    │
                   ▼                        │              grafana (provisioning como codigo)
             influxdb 2.7 (TSDB) ───────────┘                    │
             "telemetria" bucket, precision ns                   ▼
                                                        alerta >32 °C → email (Brevo SMTP)
```

## Por qué cada pieza (decisiones, no humo)

| Decisión | Alternativas descartadas | Razón |
|---|---|---|
| **MQTT** como protocolo | AMQP, CoAP | El laboratorio deja elegir uno. MQTT es el único con broker estándar en Docker (Mosquitto), QoS 1 medible por mensaje (PUBACK) y sin gateway intermedio. AMQP 0-9-1 con RabbitMQ exige más gluing y CoAP exige el gateway que ya construimos en el Lab 4. |
| **Mosquitto** | EMQX | El lab sugiere ambos. EMQX es un monstro de Erlang con dashboard propio; Mosquitto es C, 3 MB, hace exactamente lo que necesita un salón de clase. |
| **InfluxDB 2.7** | TimescaleDB, QuestDB, Mongo, Supabase | Mongo es documento (no serie temporal: habría que diseñar el esquema y las agregaciones a mano) y Supabase es nube externa (este lab es "plataforma propia"). Influx es TSDB nativa con integración Flux de primera clase en Grafana. |
| **Grafana aislado de la BD** | un solo contenedor "todo en uno" | Requisito explícito: Grafana solo *lee* la TSDB por su API, con un token de **solo-lectura** creado a propósito (`docker/crear_token_reader.sh`), y ningún puerto se publica al host salvo por nginx. |
| **Alerta por email con Brevo** | webhook, log | Se conecta con el Lab 3 (reglas de IoT Central) y esta vez la regla vive en Grafana: si la media de los últimos 10 min supera 32 °C durante 2 min → email. Umbral: el rango físico del escenario es 16–32 °C, así que **la alerta nunca dispara sola** — se fuerza desde el publicador. |
| **Docker Compose** | procesos sueltos (como el Lab 4) | Lo pide el laboratorio y hace el stack reproducible: `docker compose up -d --build` desde cero. |
| **/taller5 en el mismo dominio** | subdominio nuevo, otra VM | La VM tiene 892 MB + 2 GB de swap y el stack consume ~204 MB medidos — cabe. Reutiliza nginx + Let's Encrypt que ya frontean el taller 4 en `/` (quedó intacto y sirviendo). |

## Estructura

```
docker/           compose, mosquitto.conf, Dockerfile.python, provisioning de
                  Grafana (datasource + dashboard + reglas de alerta) — TODO como codigo
python/           publisher.py, ingest.py, test_python.py
dashboard/        pagina didactica Flask (la del Lab 4 "ver los mensajes", en vivo)
tools/            vmexec.py / vmsudo.py / vm_sync.py — los del Lab 5 (acceso por
                  key a la VM 52.159.94.196). Los demas (dash_deploy, vm_https,
                  vm_push/pull, vm_robustez, vm_reboot_test) son heredados del
                  Lab 4 y siguen apuntando a su dashboard y a la VM anterior
evidencias/       Anexo grafico (4 PNG) + logs crudos (jsonl) + logs de la alerta
docs/bitacora.md  el diario del taller, con errores y soluciones reales
informe-lab5.md   el informe completo (10 secciones + anexo de evidencias)
Informe_Lab5_Jose_Tellez_U00060479.pdf   el mismo informe, imprimible (4 pags)
```

## Entrega (qué mirar primero)

| Pieza | Dónde |
|---|---|
| Informe final en PDF | `Informe_Lab5_Jose_Tellez_U00060479.pdf` — 4 páginas, con el anexo de evidencias al final |
| Informe en Markdown | `informe-lab5.md` — misma información, editable |
| Anexo gráfico (Evid. 1–4) | `evidencias/README.md` como índice; PNG sueltos en `evidencias/` |
| Bitácora (qué falló y cómo) | `docs/bitacora.md` — decisiones, 8 errores reales, el incidente de la VM y el cierre |
| Reproducir desde cero | este README, sección "Cómo levantar la VM desde cero" |

## Cómo levantar la VM desde cero

```bash
# 0. VM nueva con Ubuntu 22+/24, misma red de seguridad que el Lab 4 (abrir 80/443)
curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker $USER

# 1. subir el repo
git clone <repo> && cd Iot_learning/taller_5_iot
cp ../taller_4_iot/.env .env    # VM_HOST / VM_USER / VM_PASS
#    (para la VM del Lab 5 se usa VM_KEY: ruta al .pem, en vez de VM_PASS)

# 2. configurar secretos (NUNCA en git)
cd docker && cp .env.example .env && nano .env
#    generar los aleatorios con: openssl rand -hex 24
#    BREVO_EMAIL y BREVO_SMTP_KEY: la "SMTP key" del panel de Brevo (NO la API key)

# 3. stack
docker compose up -d --build
bash crear_token_reader.sh          # token SOLO-LECTURA para Grafana
docker compose up -d grafana        # recrear con el token real

# 4. dashboard didactico (systemd) + nginx (bloque /taller5/ + /taller5/grafana/)
sudo cp taller5-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now taller5-dashboard
bash instalar_nginx.sh

# 5. (una vez, Lab 4) HTTPS: ver ../taller_4_iot/tools/vm_https.py
```

## URLs

| Qué | Dónde |
|---|---|
| Sala de control Lab 4 (intacta) | https://iotcentraljose.duckdns.org/ |
| **Página didáctica Lab 5** (cómo viaja cada mensaje, en vivo) | https://iotcentraljose.duckdns.org/taller5/ |
| **Grafana** (dashboard 4 días; Viewer anónimo, admin con `GRAFANA_ADMIN_PASSWORD`) | https://iotcentraljose.duckdns.org/taller5/grafana/d/lab5 |
| JSON del estado | https://iotcentraljose.duckdns.org/taller5/api/estado |

## Operación

```bash
cd ~/taller_5_iot/docker
docker compose ps                        # estado
docker compose logs -f ingest            # que entra a la TSDB
docker stats --no-stream                 # memoria (techo ~832MB, real ~204MB)
docker exec taller5-influxdb influx query \
  'from(bucket:"telemetria") |> range(start:-1d) |> filter(fn:(r)=>r._field=="Temperature") |> count()' --org unab
```

**Forzar la alerta (prueba del laboratorio):**
```bash
docker compose run --rm --no-deps publisher python -u python/publisher.py \
  --interval 10 --duration 600 --caliente --client-suffix force
```
En 2–3 min la regla pasa a *Firing* (o ~10 min: es media móvil de 10 min + `for:
2m`); ver el evento en Grafana → Alerting →
Alert rules → `lab5-temp-32` (captura en `evidencias/alerta/`). El email llega a
`ALERT_TO_EMAIL`. **Credenciales Brevo (el error que hicimos perder una hora):**
`BREVO_EMAIL` es el **usuario relay** que Brevo asigna — se lee en
`curl https://api.brevo.com/v3/account -H "api-key: xkeysib-…"` →
`relay.data.userName` (algo como `b8cab8001@smtp-brevo.com`) — NO el email de la
cuenta; `BREVO_SMTP_KEY` es la **SMTP key** (`xsmtpsib-…`) del panel SMTP & SMTP
API, no la API key REST (`xkeysib-…`). Probar con `bash docker/probar_brevo.sh`
→ esperado `LOGIN_OK`.

**Corrida de la toma (historia real):** la primera corrida arrancó el
2026-10-07 ~23:21 UTC (los `live-*.jsonl` se reiniciaron a propósito para que
la evidencia empiece en cero), pero **la VM original se perdió** el 16-oct
(la desasignó Azure y su disco era temporal → se fue InfluxDB y la toma; ver
`docs/bitacora.md`, sección 3). Todo se reconstruyó en una **VM nueva**
(`52.159.94.196`, disco persistente, snapshot y cron de DuckDNS) y la toma
definitiva arrancó el **2026-10-17 04:51 UTC**, esta vez **por bloques
encendido/apagado** por indicación del profesor, para observar el sistema sin
datos. Corte: **2026-10-22 05:22 UTC** → 4 bloques ON (173 · 1 033 · 1 302 ·
1 677 muestras) y 3 huecos, 4 185 muestras en total sobre una ventana de 5
días. Los huecos están documentados en `docs/bitacora.md` (sección 4) y en la
sección 5 del informe.

## Seguridad

- Nada escucha en `0.0.0.0` salvo nginx (80/443, TLS Let's Encrypt). Comprobado:
  `python3 -c "import socket; socket.create_connection(('VM',3000),3)"` falla
  para 3000/8086/8090/1883/8080.
- Mosquitto sin contraseña **solo dentro de la red del compose** (1883 sin publicar).
- Grafana → Influx con token de solo-lectura; Influx → escritura solo desde el
  contenedor ingest.
- `.env` gitignoreado; los secretos se generan en la VM y nunca viajan por chat/git.
- La SMTP key de Brevo apareció en un chat: **rotarla** tras el laboratorio.
