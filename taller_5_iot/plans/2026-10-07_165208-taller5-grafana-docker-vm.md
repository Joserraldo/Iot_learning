# Plan — Laboratorio 5 IoT: plataforma propia (Mosquitto + InfluxDB + Grafana + Brevo) en la misma VM, bajo `/taller5`

## Goal

Montar en la VM de Azure existente (`52.237.172.24`) el stack del Lab 5 — publicador MQTT → broker Mosquitto → TSDB InfluxDB → Grafana con alerta de temperatura por email vía Brevo — con Docker Compose, servido detrás de nginx en `https://iotcentraljose.duckdns.org/taller5/` (Grafana en `/taller5/grafana/`), dejando el dashboard del taller 4 intacto en la raíz, y dejar la toma de 4 días corriendo con página didáctica estilo taller 4.

## Current context / assumptions

- **Repo local:** `D:\José Tellez\Documents\universidad\sexto semestre\Iot_learning\taller_5_iot\` (solo tiene `laboratorio_5.md` + PDF; todo lo demás se crea aquí). Los talleres 2–4 viven al mismo nivel; el taller 4 es el precedente de infra.
- **VM:** `52.237.172.24`, user `azureuser`, mismo acceso del taller 4 (herramientas `tools/vm_push.py`, `tools/vmexec.py` del `taller_4_iot` usan las credenciales del `.env` de esa carpeta — mismo `.pem`/`VM_PASS`). 896 MB RAM + swap de 2 GB ya configurada (`vm_robustez.py`), 2 vCPU, ~23 GB libres, CPU ~5 %.
- **Dominio:** `iotcentraljose.duckdns.org` ya apunta a la VM con TLS de Let's Encrypt (certbot.timer). nginx ya da servicio al dashboard Flask del taller 4 en `/` (gunicorn 127.0.0.1:8080, systemd `taller4-dashboard`). **No hay que tocar DNS ni NSG**: reusamos 80/443.
- **Decisión de subruta (respuesta al "¿cabe?"):** SÍ cabe. El taller 4 consume ~111 MB; el stack nuevo añade ~350–450 MB acotados por límites de memoria en compose, y hay swap de 2 GB. **No movemos el taller 4 de `/`** (sus plantillas usan rutas absolutas `/api/...` y es la sala de control viva de la clase anterior — tocarlo es riesgo sin beneficio). `/taller5` es suficiente: el dominio raíz ya ES el taller 4.
- **Protocolo:** MQTT sobre Mosquitto local (elegido y declarado en el informe: es el único de los tres con broker estándar en Docker, sin gateway, latencia medible VM→VM). AMQP/CoAP se descartan explícitamente (YAGNI — el lab permite elegir uno).
- **Base de datos:** InfluxDB v2 en contenedor (TSDB nativa, integración Flux de primera clase con Grafana). **No** Mongo ni Supabase: Mongo no es TSDB (hay que escribir el esquema/queries de series a mano) y Supabase es servicio externo — el requisito del usuario es "todo local en la VM, sin depender de servicios externos". Lo único externo permitido: Brevo SMTP para el email de alerta (es la condición del ejercicio).
- **Brevo:** el usuario debe proporcionar su SMTP key (se pone solo en `/home/azureuser/taller_5_iot/.env` de la VM, nunca en git ni en el informe). Recordarle rotarla si la pega en el chat.
- **Escenario:** mismas 3 variables `Temperature`/`Humidity`/`Iluminance` con random-walk ±0.5 del `python/common.py` del taller 4. Rango de temperatura 16–32 °C → la alerta (>32 °C) **nunca** dispara sola: se fuerza con flag `--caliente` del publicador (eso es exactamente lo que pide el lab: "forzar el valor desde el publicador").
- **Cadencia:** 60 s → 1440 muestras/día, ~15 KB/día en Influx. La ventana de 4 días empieza en la sesión 1.
- Shell local: git-bash en Windows; comandos VM: siempre vía `python tools/vmexec.py "<cmd>"` (paramiko, ejecuta como azureuser; para sudo ver nota en Task 0).

## Architecture

```
                      VM 52.237.172.24 — docker compose (red interna, restart: always)
┌────────────┐  MQTT   ┌────────────┐  sub    ┌────────────┐  Flux/HTTP ┌───────────┐
│ publisher  │────────▶│ mosquitto  │────────▶│  ingest    │───────────▶│ influxdb  │
│ (python/   │ 127.0.0.1│ (broker)   │         │ (python/   │  line proto│ (TSDB)    │
│ paho)      │  :1883  └────────────┘         │  ingesta)  │            └─────┬─────┘
└─────┬──────┘                                └─────┬──────┘                  │ datasource (proxy)
      │ live.jsonl (evidencia por mensaje)          │ live.jsonl              ▼
      ▼                                             ▼                    ┌───────────┐  email SMTP
┌───────────────────────────────────────────────────────────┐           │  grafana  │──────────▶ Brevo
│ Flask didáctico :8090 (solo 127.0.0.1)  "/taller5/"        │           │  :3000    │  (alerta T>32)
└───────────────────────────▲───────────────────────────────┘           └─────┬─────┘
                            │                                                  │
              nginx ────────┴──  https://iotcentraljose.duckdns.org/taller5/ ──┘  /taller5/grafana/
                                    y /  (taller 4, intacto)
```

- Grafana queda **aislado de la BD**: contenedor separado, solo lee por la API Flux con token de solo-lectura; InfluxDB **sin puerto publicado** en el host.
- Ningún servicio nuevo escucha en 0.0.0.0: todo entra por nginx (80/443) → la puerta TLS-no-cifrada que aprendimos a cerrar en el taller 4 no se abre nunca.

## Repositorio local a crear (`taller_5_iot/`)

```
taller_5_iot/
  README.md                 # cómo levantar la VM, sin secretos
  docker/docker-compose.yml
  docker/.env.example
  docker/mosquitto.conf
  docker/grafana/provisioning/datasources/influx.yml
  docker/grafana/dashboards/lab5.json      # exportado al final (Task 7)
  python/publisher.py
  python/ingest.py
  python/test_python.py     # checks falla-primero de las 2 funciones puras
  dashboard/app.py
  dashboard/templates/index.html
  tools/  (copiados de ../taller_4_iot/tools: vm_push.py vm_pull.py vmexec.py)
  docs/bitacora.md
  informe-lab5.md
  evidencias/
```

---

## Step-by-step tasks

### Task 0 — Verificar capacidad e instalar Docker en la VM (10 min)

Credenciales VM: `cp ../taller_4_iot/.env .env` (mismo `.env` del taller 4 — VM_HOST/VM_USER/VM_PASS) y copiar tools: `cp -r ../taller_4_iot/tools tools`.

```bash
python tools/vmexec.py "free -m | awk '/Mem/{print \"RAM_libre_MB=\"\$7}'; df -h / | awk 'NR==2{print \"Disco_libre=\"\$4}'; swapon --show | head -1; docker --version 2>&1; docker compose version 2>&1"
```
**Esperado:** `RAM_libre_MB=…`, `Disco_libre=1xG`+, `RAM_libre_MB` puede ser bajo (<100) — es normal con swap; si `swapon --show` sale vacío → **STOP**, la swap del taller 4 se perdió, rehacer con `../taller_4_iot/tools/vm_robustez.py`.

Si `docker: command not found` (probable — el taller 4 no usó docker), instalar (sudo por SSH: ejecutar con paramiko escribiendo la contraseña en stdin, o en una sesión interactiva `ssh azureuser@52.237.172.24` con el mismo `.pem`). **Un solo bloque:**

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker azureuser
```
**Verificar** (la siguiente `vmexec` ya entra con grupo docker tras reconexión; si no, usar `sudo docker`):
```bash
python tools/vmexec.py "docker run --rm hello-world | grep -c 'Hello from Docker'"
```
**Esperado:** `1`. Si `docker compose version` da `v2.x`, seguimos. **Capacidad:** 896 MB + swap 2 GB + ~350 MB de contenedores acotados (limits en compose) → **cabe; el /taller4 no hace falta ni se crea** (taller 4 se queda en `/`, documentado en README).

Commit: `git add tools .env.example-already-ignored && git commit -m "taller5: herramientas VM reutilizadas del taller 4"` (`.env` debe estar en `.gitignore`; si el repo no lo tiene, `printf '.env\n__pycache__/\n*.pyc\n' >> .gitignore`).

### Task 1 — `docker/docker-compose.yml` + `.env.example` + mosquitto.conf (15 min)

`docker/.env.example` (el real se crea en la VM, **nunca** se commitea):
```dotenv
# Copiar a .env en la VM y rellenar. NUNCA commitear.
GRAFANA_ADMIN_PASSWORD=<elige una>
INFLUX_ORG=unab
INFLUX_BUCKET=telemetria
INFLUX_USERNAME=iot
INFLUX_PASSWORD=<elige una>
INFLUX_API_TOKEN=<token largo aleatorio, p.ej. openssl rand -hex 24>
INFLUX_TOKEN_READER=<token SOLO-LECTURA para Grafana, se crea en Task 3>
BREVO_SMTP_KEY=<smtp key de Brevo del usuario>
DASH5_KEY=<clave de los endpoints de escritura del didactico, openssl rand -hex 12>
```

`docker/mosquitto.conf`:
```conf
listener 1883
allow_anonymous true
persistence true
persistence_location /data/
```
(Sin autenticación porque 1883 **no** se publica al host — solo contenedores de la red interna; anotado en Riesgos.)

`docker/docker-compose.yml` (poner `ports: "127.0.0.1:…"` en todo lo publicado — lección del taller 4):
```yaml
name: taller5
services:
  mosquitto:
    image: eclipse-mosquitto:2
    volumes: ["./mosquitto.conf:/mosquitto/config/mosquitto.conf:ro", "mqtt_data:/mosquitto/data"]
    restart: always
    mem_limit: 64m
  influxdb:
    image: influxdb:2.7
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: ${INFLUX_USERNAME}
      DOCKER_INFLUXDB_INIT_PASSWORD: ${INFLUX_PASSWORD}
      DOCKER_INFLUXDB_INIT_ORG: ${INFLUX_ORG}
      DOCKER_INFLUXDB_INIT_BUCKET: ${INFLUX_BUCKET}
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: ${INFLUX_API_TOKEN}
    volumes: ["influx_data:/var/lib/influxdb2"]
    restart: always
    mem_limit: 320m
    # SIN ports: solo accesible por la red interna (Grafana/dash via host:8086? no -> ingest via red)
  ingest:
    build: { context: .., dockerfile: docker/Dockerfile.python }
    command: ["python", "-u", "python/ingest.py"]
    environment:
      MQTT_HOST: mosquitto
      INFLUX_URL: http://influxdb:8086
      INFLUX_ORG: ${INFLUX_ORG}
      INFLUX_BUCKET: ${INFLUX_BUCKET}
      INFLUX_TOKEN: ${INFLUX_API_TOKEN}
      LIVE_JSONL: /data/evidencias/live-ingest.jsonl
    volumes: ["../evidencias:/data/evidencias"]
    restart: always
    depends_on: [mosquitto, influxdb]
    mem_limit: 96m
  publisher:
    build: { context: .., dockerfile: docker/Dockerfile.python }
    command: ["python", "-u", "python/publisher.py", "--interval", "60"]
    environment:
      MQTT_HOST: mosquitto
      LIVE_JSONL: /data/evidencias/live-publisher.jsonl
    volumes: ["../evidencias:/data/evidencias"]
    restart: always
    depends_on: [mosquitto]
    mem_limit: 96m
  grafana:
    image: grafana/grafana:11.2.0
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}
      GF_SERVER_ROOT_URL: https://iotcentraljose.duckdns.org/taller5/grafana/
      GF_SERVER_SERVE_FROM_SUB_PATH: "true"
      GF_AUTH_ANONYMOUS_ENABLED: "true"
      GF_AUTH_ANONYMOUS_ORG_ROLE: Viewer
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_ANALYTICS_REPORTING_ENABLED: "false"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
    ports: ["127.0.0.1:3000:3000"]
    restart: always
    depends_on: [influxdb]
    mem_limit: 256m
volumes: { mqtt_data: {}, influx_data: {}, grafana_data: {} }
```

`docker/Dockerfile.python`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY python/ python/
RUN pip install --no-cache-dir "paho-mqtt>=1.6,<2.0" requests
CMD ["python", "-u", "python/publisher.py"]
```

### Task 2 — Prueba fallida → implementer del publicador y el ingestor (TDD, 25 min)

Primero `python/test_python.py` (las funciones puras: payload y línea de Influx):
```python
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import publisher, ingest

# 1) payload: 3 variables, rangos del escenario, ts en ns
p = json.loads(publisher.payload_json(lectura={"Temperature": 24.0, "Humidity": 50.0, "Iluminance": 400.0}))
assert set(p) == {"Temperature", "Humidity", "Iluminance", "ts_ns"}, p.keys()
assert isinstance(p["ts_ns"], int) and p["ts_ns"] > 10**18

# 2) modo caliente: temperatura fuera de rango (para forzar la alerta)
for _ in range(50):
    assert publisher.generar_lectura(caliente=True)["Temperature"] > 32.0

# 3) linea de influx: medicion telemetria, 3 campos float, precision ns
line = ingest.to_line_protocol({"Temperature": 24.1, "Humidity": 50.2, "Iluminance": 400.3, "ts_ns": 1700000000000000000})
assert line.startswith("telemetria ")
assert "Temperature=24.1" in line and line.endswith(" 1700000000000000000")

print("OK 3/3")
```
```bash
python3 python/test_python.py   # (o C:/Program Files/Python313/python.exe)
```
**Esperado AHORA:** `ModuleNotFoundError: No module named 'publisher'` (fail confirmado). Escribir `publisher.py` y `ingest.py` abajo, volver a correr → **esperado `OK 3/3`**.

`python/publisher.py`:
```python
#!/usr/bin/env python3
"""Publicador Lab 5: random-walk de las 3 variables del escenario (mismo
comportamiento que taller_4_iot/python/common.py) -> MQTT -> mosquitto local.
Evidencia: 1 linea JSONL por mensaje publicado (live-publisher.jsonl).
--caliente fuerza Temperature 33-38 C para disparar la alerta de Grafana.
"""
import argparse, json, os, random, time
import paho.mqtt.client as mqtt

LIMITS = {"Temperature": (16.0, 32.0), "Humidity": (35.0, 70.0), "Iluminance": (100.0, 800.0)}
_state = {"Temperature": 24.0, "Humidity": 50.0, "Iluminance": 400.0}

def generar_lectura(caliente: bool = False) -> dict:
    for k, (lo, hi) in LIMITS.items():
        _state[k] = round(min(hi, max(lo, _state[k] + random.uniform(-0.5, 0.5))), 1)
    if caliente:
        _state["Temperature"] = round(random.uniform(33.0, 38.0), 1)
    return dict(_state)

def payload_json(lectura: dict) -> str:
    d = dict(lectura); d["ts_ns"] = time.time_ns()
    return json.dumps(d)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--duration", type=int, default=0, help="0 = infinito (corrida de 4 dias)")
    ap.add_argument("--caliente", action="store_true", help="Temperature 33-38 C (probar alerta)")
    args = ap.parse_args()
    host = os.environ.get("MQTT_HOST", "127.0.0.1")
    logf = os.environ.get("LIVE_JSONL", "evidencias/live-publisher.jsonl")
    os.makedirs(os.path.dirname(logf) or ".", exist_ok=True)
    client = mqtt.Client(client_id="lab5-publisher")
    client.connect(host, 1883, 30)
    t0, seq = time.time(), 0
    while args.duration == 0 or time.time() - t0 < args.duration:
        lec = generar_lectura(caliente=args.caliente)
        s = payload_json(lec)
        t_pub = time.monotonic()
        r = client.publish("lab5/telemetria", s, qos=1)
        r.wait_for_publish(timeout=10)
        rt = round((time.monotonic() - t_pub) * 1000, 1)
        seq += 1
        line = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seq": seq,
                "proto": "MQTT", "topic": "lab5/telemetria", "bytes": len(s.encode()),
                "payload": json.loads(s), "puback_ms": rt}
        with open(logf, "a") as f: f.write(json.dumps(line) + "\n")
        print(f"[MQTT] #{seq} T={lec['Temperature']} H={lec['Humidity']} L={lec['Iluminance']} puback {rt} ms", flush=True)
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
```

`python/ingest.py`:
```python
#!/usr/bin/env python3
"""Ingestor Lab 5: broker MQTT -> InfluxDB v2 (line protocol) + evidencia JSONL.
Mide el salto broker->ingestor (latencia del mensaje dentro de la VM).
"""
import json, os, time
import paho.mqtt.client as mqtt
import requests

def to_line_protocol(d: dict) -> str:
    fields = ",".join(f"{k}={d[k]}" for k in ("Temperature", "Humidity", "Iluminance"))
    return f"telemetria {fields} {d['ts_ns']}"

def main():
    host = os.environ.get("MQTT_HOST", "127.0.0.1")
    url = os.environ.get("INFLUX_URL", "http://127.0.0.1:8086")
    org, bucket, token = (os.environ[k] for k in ("INFLUX_ORG", "INFLUX_BUCKET", "INFLUX_TOKEN"))
    logf = os.environ.get("LIVE_JSONL", "evidencias/live-ingest.jsonl")
    write_url = f"{url}/api/v2/write?org={org}&bucket={bucket}&precision=ns"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "text/plain"}
    seq = 0
    def on_message(_c, _u, msg):
        nonlocal seq
        t_rx = time.time()
        d = json.loads(msg.payload.decode())
        hop_ms = round((t_rx - d["ts_ns"] / 1e6) * 1000, 1)   # pub->ingest (reloj de la misma VM)
        r = requests.post(write_url, headers=headers, data=to_line_protocol(d), timeout=10)
        seq += 1
        line = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seq": seq,
                "payload": d, "hop_ms": hop_ms, "influx_status": r.status_code}
        with open(logf, "a") as f: f.write(json.dumps(line) + "\n")
        print(f"[INGEST] #{seq} hop {hop_ms} ms influx {r.status_code}", flush=True)
        if r.status_code not in (204,):
            raise RuntimeError(f"influx write failed: {r.text[:200]}")
    c = mqtt.Client(client_id="lab5-ingest")
    c.on_message = on_message
    c.connect(host, 1883, 30)
    c.subscribe("lab5/telemetria", qos=1)
    c.loop_forever()

if __name__ == "__main__":
    main()
```
Commit: `git add taller_5_iot/python taller_5_iot/docker && git commit -m "taller5: publicador MQTT + ingestor a InfluxDB con tests"`

### Task 3 — Levantar el stack en la VM y verificar datos en InfluxDB (20 min)

```bash
python tools/vm_push.py taller_5_iot/docker taller_5_iot/python taller_5_iot/dashboard  # (vm_push sube arboles; si firma rutas, alternar: scp -r via same .pem)
python tools/vmexec.py "mkdir -p ~/taller_5_iot/evidencias"
```
Crear `.env` en la VM (`nano ~/taller_5_iot/docker/.env`, valores del `.env.example`, generar secretos con `openssl rand -hex 24`). **El token y contraseñas no pasan por el chat.**

```bash
python tools/vmexec.py "cd ~/taller_5_iot/docker && docker compose up -d --build"
```
**Esperado:** `Container taller5-grafana-1 Started` (6 containers). Influx tarda ~20 s en el setup inicial.

Verificación en cadena (una sola corrida, cada una con su esperado):
```bash
python tools/vmexec.py "sleep 25; docker ps --format '{{.Names}} {{.Status}}' | grep taller5"
```
→ 6 líneas `… Up`.
```bash
python tools/vmexec.py "tail -3 ~/taller_5_iot/evidencias/live-publisher.jsonl"
```
→ líneas JSON con `"puback_ms": <número>` (primer mensaje a los ~60 s de arrancar publisher; si aún no hay, `docker compose logs publisher --tail`).
```bash
python tools/vmexec.py "docker exec taller5-influxdb-1 influx query 'from(bucket:\"telemetria\") |> range(start:-10m) |> filter(fn:(r)=>r._field==\"Temperature\") |> last()' -o json"
```
→ JSON con `_value` ≈ 16–32. **Esto prueba publicador → broker → ingestor → TSDB end-to-end.**

Crear el token de SOLO-LECTURA para Grafana con la API de Influx (token admin desde el `.env` de la VM — se lee allí, nunca se pega en el chat). Comando exacto, corriendo EN la VM:
```bash
cd ~/taller_5_iot/docker && source <(grep -E '^(INFLUX_API_TOKEN|INFLUX_ORG)=' .env | sed 's/^/export /') && \
curl -s -X POST http://localhost:8086/api/v2/authorizations \
  -H "Authorization: Bearer $INFLUX_API_TOKEN" -H 'Content-Type: application/json' \
  -d '{"orgID":"'$(curl -s http://localhost:8086/api/v2/orgs -H "Authorization: Bearer $INFLUX_API_TOKEN" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)'","bucketIDs":[],"permissions":[{"action":"read","resource":{"type":"org"}}]}' | tee /tmp/reader-auth.json | head -c 200
```
→ esperado JSON con `"token": "…"`. Copiar ese token a `INFLUX_TOKEN_READER` en `.env` y `docker compose up -d grafana` para que el `${INFLUX_TOKEN_READER}` de la datasource se resuelva.

Commit: `git commit -m "taller5: stack compose verificado — datos fluyen a InfluxDB"` (solo docs/README si cambió algo local; nada de `.env`).

### Task 4 — Grafana provisionado como código: datasource + dashboard (25 min)

`docker/grafana/provisioning/datasources/influx.yml` (auth Flux documentada: usuario `token`, password = token reader; `$ENV` lo sustituye Grafana):
```yaml
apiVersion: 1
datasources:
  - name: InfluxDB
    type: influxdb
    access: proxy
    url: http://influxdb:8086
    basicAuth: true
    basicAuthUser: token
    secureJsonData:
      basicAuthPassword: ${INFLUX_TOKEN_READER}
    jsonData:
      version: Flux
      organization: ${INFLUX_ORG}
      defaultBucket: ${INFLUX_BUCKET}
```
Grafana necesita ver el env: añadir a `environment` del servicio grafana `INFLUX_TOKEN_READER: ${INFLUX_TOKEN_READER}` etc. (la sustitución `$ENV` en provisioning lee las variables del proceso grafana). Redeploy: `cd ~/taller_5_iot/docker && docker compose up -d grafana`.

**Verificar datasource por API** (más fiable que mirar la UI). Comando exacto, corriendo EN la VM (la contraseña admin se lee del `.env` de la VM, no se escribe en el chat):
```bash
cd ~/taller_5_iot/docker && source <(grep -E '^GRAFANA_ADMIN_PASSWORD=' .env | sed 's/^/export /') && \
curl -s "http://127.0.0.1:3000/taller5/grafana/api/datasources" -u "admin:$GRAFANA_ADMIN_PASSWORD" | grep -o '"name": *"[^"]*"'
```
→ esperado: `"name": "InfluxDB"`. Y health:
```bash
curl -s http://127.0.0.1:3000/taller5/grafana/api/health
```
→ esperado `"database": "ok"`.

Dashboard: crearlo en la UI una vez (sesión de clase es aceptable, pero para rubrica de "stack reproducible") se construye por API con `docker/grafana/dashboards/lab5.json` provisionado — JSON mínimo válido: 4 time-series (uno por variable + temperatura con umbral 32 como línea) y 2 stat con unidad °C/%. Contenido completo del JSON en la implementación: usar `write_file` con el template que se exporta al final de esta tarea vía:
```bash
curl -s "http://127.0.0.1:3000/taller5/grafana/api/dashboards/uid/lab5" -u "admin:$GRAFANA_ADMIN_PASSWORD" | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['dashboard'], indent=1))" > ~/taller_5_iot/docker/grafana/dashboards/lab5.json
```
`docker/grafana/provisioning/dashboards/all.yml`:
```yaml
apiVersion: 1
providers:
  - name: lab5
    folder: Lab5
    type: file
    options: { path: /var/lib/grafana/dashboards }
```
(Con esto, el dashboard editado en la UI se exporta al repo → commiteado → reproducible desde cero.)
**Verificación de la ventana de 4 días:** el dashboard usa `timeRange: {from: "now-4d", to: "now"}`; al inicio solo hay ~0 días — el informe declara la fecha de inicio y corte (el lab lo permite explícitamente).

### Task 5 — Alerta de umbral → email por Brevo, forzada desde el publicador (20 min)

En Grafana (contact point + alerta se pueden crear por API; hacerlos en la UI y exportar, o con los 2 curl de abajo):

1. **Contact point** (SMTP Brevo — `smtp-relay.brevo.com:587`, user = email de la cuenta Brevo, password = SMTP key → `INFLUX`… no: variables `BREVO_SMTP_KEY` y `BREVO_EMAIL` van al compose de grafana como `GF_SMTP_*`):
```yaml
# añadir al environment de grafana en compose:
      GF_SMTP_ENABLED: "true"
      GF_SMTP_HOST: smtp-relay.brevo.com:587
      GF_SMTP_USER: ${BREVO_EMAIL}
      GF_SMTP_PASSWORD: ${BREVO_SMTP_KEY}
      GF_SMTP_FROM_ADDRESS: ${BREVO_EMAIL}
```
`docker compose up -d grafana`. **Test de envío** (usa el endpoint de test de Grafana):
```bash
curl -s -X POST "http://127.0.0.1:3000/taller5/grafana/api/alerting/notifications/test-receiver" \
  -u "admin:$GRAFANA_ADMIN_PASSWORD" -H 'Content-Type: application/json' \
  -d '{"name":"brevo-test","type":"email","settings":{"addresses":"<tu email personal>","tags":"","singleEmail":true}}' -w '\n%{http_code}\n'
```
→ esperado `200` y email real recibido. (Brevo limita a 300 emails/día en plan gratis — suficiente.)

2. **Alert rule:** condición `Temperature > 32 °C`, ventana "for 2m" (query Flux: `last()` del bucket por `device=lab5`), acción: contact point Brevo. Crearla por la UI una vez y dejar captura; opcionalmente por API POST `/api/v1/provisioning/alert-rules`.

3. **Forzar el disparo** (requisito del lab — "forzar el valor desde el publicador"): el publisher normal sigue corriendo; lanzar un segundo contenedor efímero con el mismo client_id NO (dos identidades MQTT se pisan — lección del taller 4 con el gateway; aquí el broker lo tolera pero la evidencia se mezcla). Hacerlo con `--interval 10 --duration 300 --caliente` dentro de la red del contenedor publisher:
```bash
docker compose run --rm publisher python -u python/publisher.py --interval 10 --duration 300 --caliente --client-suffix force
```
→ añadir al publisher el flag `--client-suffix` que concatena al `client_id` (una línea: `client_id="lab5-publisher"+suffix`). Esperado stdout: `[MQTT] #1 T=33.4 …`. En 2–3 min la alerta pasa a Pending→Firing y llega el email. **Evidencia:** captura del estado Firing + del email + `grep caliente`… no: la linea jsonl con `"Temperature": 3x.x` en `live-publisher.jsonl` queda como evidencia dura. Copiar las capturas a `evidencias/alerta/`.

Commit: `git commit -m "taller5: alerta Grafana>32C con email Brevo, disparo forzado verificado"`.

### Task 6 — Página didáctica `/taller5/` (estilo "cómo viaja el mensaje" del taller 4) (30 min)

`dashboard/app.py` — Flask mínimo (rutas **sin prefijo**; nginx lo frontea en `/taller5/`; el HTML usa **solo URLs relativas** para que funcione bajo el prefijo):
```python
#!/usr/bin/env python3
"""Pagina didactica Lab 5: muestra en vivo como viaja el mensaje
publicador -> mosquitto -> ingestor -> InfluxDB -> Grafana.
Sin estado; lee los jsonl de evidencia (append-only)."""
import json, os
from flask import Flask, jsonify, render_template

app = Flask(__name__)
EV = os.environ.get("EVIDENCIAS", "/home/azureuser/taller_5_iot/evidencias")

def tail_jsonl(path, n=60):
    if not os.path.exists(path):
        return []
    with open(path, "rb") as f:
        f.seek(0, 2); size = f.tell(); f.seek(max(0, size - 300_000))
        lines = f.read().decode("utf-8", "replace").splitlines()
    return [json.loads(l) for l in lines[-n:]][::-1]

@app.get("/api/estado")
def estado():
    pub = tail_jsonl(f"{EV}/live-publisher.jsonl")
    ing = tail_jsonl(f"{EV}/live-ingest.jsonl")
    return jsonify(publisher=pub, ingest=ing,
                   total_publicados=len(open(f"{EV}/live-publisher.jsonl").readlines()) if os.path.exists(f"{EV}/live-publisher.jsonl") else 0)

@app.get("/")
def index():
    return render_template("index.html")
```
Ejecutar con gunicorn **solo en loopback** (systemd, mismo patrón que `taller4-dashboard`):
`/etc/systemd/system/taller5-dashboard.service`:
```ini
[Unit]
Description=Lab5 dashboard didactico
After=network.target docker.service

[Service]
User=azureuser
WorkingDirectory=/home/azureuser/taller_5_iot/dashboard
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/azureuser/taller_4_iot/.venv/bin/gunicorn -w 1 --threads 2 -b 127.0.0.1:8090 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```
(Reusar el venv del taller 4 que ya tiene flask+gunicorn; si falta, `~/taller_4_iot/.venv/bin/pip install flask gunicorn`.)

`dashboard/templates/index.html` — una página, estilo taller 4 (mismo lenguaje visual que `taller_4_iot/dashboard/templates/index.html`: copiar su CSS/base si reutiliza, o 120 líneas propias): título "¿Cómo viaja un mensaje?", las 5 etapas como tarjetas con el dato en vivo (seq, puback_ms de la última línea del jsonl del publisher → broker → hop_ms → influx_status → "visible en Grafana <a href=\"grafana/dashboards/…\">"), tabla con las 20 últimas líneas crudas (`[MQTT] #123 … puback 8.4 ms` — la exigencia didáctica del usuario), glosario corto, y enlace grande "Abrir Grafana →" apuntando a `grafana/dashboards/f/lab5` (relativo desde /taller5/... → enlazar absoluto `https://iotcentraljose.duckdns.org/taller5/grafana/`). Auto-refresco `setInterval(fetch("api/estado"), 2500)` — **relativo, sin `/` inicial**.

**Verificación dentro→fuera** (tabla del skill remote-vm-service-ops):
```bash
python tools/vmexec.py "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8090/"
```
→ `200` (antes de nginx ya responde).

### Task 7 — nginx: /taller5/ (didáctico) y /taller5/grafana/ sin tocar el / del taller 4 (15 min)

Editar `/etc/nginx/sites-available/default` (o el sitio que creó `vm_https.py`) y **insertar antes de `location /`** (el bloque default actual hace `proxy_pass http://127.0.0.1:8080`):
```nginx
    location /taller5/grafana/ {
        proxy_pass http://127.0.0.1:3000;          # SIN URI -> preserva /taller5/grafana/
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    location /taller5/ {
        proxy_pass http://127.0.0.1:8090/;         # CON / -> recorta el prefijo (URLs relativas lo compensan)
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
```
```bash
sudo nginx -t && sudo systemctl reload nginx
```
→ esperado `syntax is ok / test is successful`.

**Matriz de verificación final (desde el workstation, no desde la VM):**
```bash
curl -sI https://iotcentraljose.duckdns.org/ | head -1                        # HTTP/2 200  (taller 4 intacto)
curl -s https://iotcentraljose.duckdns.org/taller5/ | grep -c "viaja"         # >=1 (pagina didactica)
curl -s https://iotcentraljose.duckdns.org/taller5/api/estado | head -c 80    # {"ingest":[...
curl -s -o /dev/null -w '%{http_code}' https://iotcentraljose.duckdns.org/taller5/grafana/api/health   # 200
curl -sI http://iotcentraljose.duckdns.org/taller5/ | head -1                 # 301 -> https
```
Y **probar que no se abrió ninguna puerta extra**: `curl -m 5 http://52.237.172.24:3000/` → timeout/rechazo (Grafana solo loopback); `nmap`-free: `nc -z -w3 52.237.172.24 8086 3000` → ambos fallan.

Commit + push: `git commit -m "taller5: nginx /taller5 + /taller5/grafana verificados desde fuera"`.

### Task 8 — Durabilidad, evidencia y entrega (20 min, al final de la sesión 1)

1. `python tools/vmexec.py "sudo reboot"` → esperar ~30 s → re-correr la matriz del Task 7 + `docker ps` (los `restart: always` deben traer todo; systemd trae el didáctico; nginx es systemd-enabled desde el taller 4). **Esperado: todo verde sin tocar nada.**
2. Dejar corriendo la toma: la corrida de 4 días arranca con el stack del Task 3 — anotar **fecha/hora de inicio** en `docs/bitacora.md`.
3. `docs/bitacora.md`: escribir en la MISMA sesión (errores reales + solución — es criterio de rúbrica). `README.md`: cómo levantar desde cero (`cp .env.example .env && docker compose up -d --build`, systemd del dashboard, bloque nginx), **sin secretos**.
4. `informe-lab5.md` (1–2 páginas): diagrama MQTT→Influx→Grafana, justificación del protocolo (MQTT nativo en broker Docker, sin gateway; QoS1 con puback medido), umbral 32 °C y ventana 4 días, tabla de reproducción, qué falló al instalar.
5. `evidencias/`: `live-publisher.jsonl` + `live-ingest.jsonl` (gitignored por `*.jsonl` del repo → `git add -f` si debe versionar), captura de la alerta Firing, captura del email Brevo, export del dashboard.
6. **Cierre de seguridad:** recordarle al usuario rotar la SMTP key de Brevo si la pegó en el chat, y verificar con `grep -ri "bearer\|token\|password" taller_5_iot/README.md taller_5_iot/informe-lab5.md taller_5_iot/docs/` → esperado: 0 coincidencias.

## Tests / validation (resumen del ciclo TDD aplicado)

| Qué | Test fallido primero | Pasa cuando |
|---|---|---|
| payload + modo caliente + línea Influx | `python3 python/test_python.py` → `ModuleNotFoundError` | `OK 3/3` |
| flujo end-to-end | antes del stack: `docker ps` vacío / consulta Flux 404 | `influx query … \| last()` devuelve un valor 16–32 |
| datasource Grafana | `api/datasources` sin InfluxDB | aparece `"name": "InfluxDB"` y query del panel pinta |
| Brevo | test-receiver sin credenciales → 500/timeout | 200 + email real en la bandeja |
| alerta forzada | `api/provisioning/alert-rules` en OK | estado `Firing` + email + jsonl con T>32 |
| rutas | `curl /taller5/` → 404 (nginx vie) | 200 y `api/estado` JSON |
| durabilidad | — | tras `sudo reboot`: matriz del Task 7 verde sin intervención |

No hay unit tests adicionales: lo no-trivial (parseo, líneas, umbral) está cubierto por `test_python.py`; el resto se verifica con los curls de arriba que tienen salida esperada exacta.

## Risks, tradeoffs, open questions

- **Memoria (896 MB reales):** el límite duro del proyecto. Mitigado: `mem_limit` por servicio (suma 832 MB de techo, uso real esperado ~300–400), swap 2 GB ya activa (verificar en Task 0). Si Grafana+Influx pelearan con el dashboard del taller 4 y los 3 clientes antiguos, **apagar primero** el taller 4 desde su propia sala de control (los clientes del lab 4 ya no son necesarios para el lab 5) — el dashboard Flask del 4 pesa 111 MB y puede convivir. Monitorear con `docker stats --no-stream` tras 1 h.
- **InfluxDB 2.7 en VM chica** es el punto más pesado; alternativas si mide mal: **QuestDB** (misma datasource Grafana, ~80 MB) — cambio acotado a compose + datasource + línea de ingesta (`pg` HTTP ILP, ~10 líneas). Decisión post-medición, no por fe.
- **Mosquitto sin auth**: aceptado porque 1883 no se publica al host (solo red docker interna). Si algún día se publica, es puerta abierta → dejarlo anotado en README.
- **Reloj pub→ingest**: `hop_ms` usa timestamps del mismo host (los dos contenedores comparten reloj del kernel) → válido; el informe debe decir que la latencia medida es broker→ingestor, no WAN.
- **No mover el taller 4 a `/taller4`**: decisión ponytail deliberada (el `/` ya ES el taller 4; reescribir sus rutas absolutas es riesgo para una demo viva a cambio de cosmética). El usuario propuso `/taller4`; si insiste, tarea extra: añadir `DispatcherMiddleware`/`root_path` + reescribir links — NO incluida.
- **Brevo SMTP**: requiere que el usuario cree la SMTP key ( Brevo → SMTP & SMTP API ). Open question pendiente de él: `BREVO_EMAIL` + key; si prefiere, alternativa sin código: webhook de Grafana → el propio dashboard del taller 4 registra el disparo (fallback documentado).
- **DuckDNS 30 días**: sigue vigente el riesgo del taller 4 (subdominio muerto si el update no corre); verificar que el cron del updater existe: `crontab -l | grep duck` → si vacío, reactivar el cron diario con el token (está en el HANDOFF del taller 4 como riesgo 2).
- **Vetustez de `.env` compartido**: las claves de IoT Central del taller 4 no se usan en el taller 5 (no hay Central en el lab 5 — estamos en plataforma propia). El `.env` nuevo de la VM SOLO con lo de arriba.
- **Riesgo de "servicios externos": ninguno** salvo Brevo (condición del lab) y los imagenes Docker (solo en el despliegue inicial; luego no se necesita red).

## Referencias de implementación (dónde copiar patrones)

- CSS/patrones de la página: `taller_4_iot/dashboard/templates/index.html` (tarjetas, auto-refresco, glosario "Cómo viaja el mensaje").
- Ops nginx/HTTPS/systemd: skill `remote-vm-service-ops` → `references/https-domain-and-systemd.md`, `references/durability-and-capacity.md` (swap, journald, MemoryMax, KillMode).
- Nunca `pkill -f` sobre ssh; parar contenedores solo con `docker compose stop <svc>`; el dashboard del taller 4 no se toca en esta corrida.
