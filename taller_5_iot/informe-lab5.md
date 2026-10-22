# Informe — Laboratorio 5: Visualización + reglas/alertas sobre plataforma propia

**Asignatura:** IoT + Cloud + Sistemas Distribuidos (UNAB) · **Estudiante:** José Alejandro Téllez Prada, u00060479
**Toma:** 2026-10-17 04:51 UTC → 2026-10-22 05:22 UTC (ventana de 5 días, 4 bloques de captura)
**Plataforma:** `https://iotcentraljose.duckdns.org` — VM Ubuntu Azure `52.159.94.196` (892 MB, 2 vCPU)

## 1. Diagrama implementado

```
 VM Ubuntu Azure (52.159.94.196) — Docker Compose (red interna, sin puertos públicos)
 ┌──────────────────────────────────────────────────────────────────────────┐
 │ publisher.py ──MQTT 1883──► mosquitto ──subscribe──► ingest.py          │
 │  (random-walk,        (broker,        (line protocol,  │ HTTP /api/v2/write
 │   QoS1 + jsonl         red interna)    hop_ms + jsonl) ▼
 │                  ┌─────────────────────────────────────────────┐         │
 │                  │ influxdb 2.7 · bucket telemetria · ns       │         │
 │                  └──────────────────┬──────────────────────────┘         │
 │                       Flux, token SOLO-LECTURA (Grafana aislado)         │
 │                  ┌──────────────────▼──────────────┐  alerta >32°C/2min  │
 │                  │ grafana OSS 11.2  (sub-path)    ├──► email SMTP ──────┼─► Brevo
 │  navegador ──► nginx TLS (80/443, Let's Encrypt): /taller5/ + /taller5/grafana/
 └──────────────────────────────────────────────────────────────────────────┘
```

Protocolo → TSDB → Grafana como exige el enunciado: **MQTT → InfluxDB → Grafana**.
Los contenedores no publican puertos al host (solo loopback); la única entrada es
nginx con HTTPS. El dashboard `lab5` está fijado a `now-4d` con stat de "muestras
en la ventana".

## 2. Justificación del protocolo (MQTT)

De los tres candidatos se eligió **MQTT**: (1) tiene broker canónico ligero en
contenedor (eclipse-mosquitto, ~3 MB de RAM) mientras AMQP (RabbitMQ) y CoAP
(gateway aiocoap, como en el Lab 4) añaden piezas para el mismo flujo; (2) **QoS 1
produce evidencia medible por mensaje** — el PUBACK real se registra en
`live-publisher.jsonl` (≈0.5–1.7 ms dentro de la VM); (3) es el protocolo que el
Lab 3 obligó a "abrir" (paho explícito) y conecta la plataforma propia con lo ya
validado. El publicador genera las 3 variables del escenario (`Temperature`,
`Humidity`, `Iluminance`) con el mismo random-walk y rangos de los Labs 2–4 para
que la comparación entre plataformas sea justa; la marca de tiempo (ns) nace en
el publicador, no en el broker.

## 3. TSDB y aislamiento de Grafana

**InfluxDB 2.7** sobre MongoDB/Supabase: Mongo no es serie temporal (habría que
diseñar esquema y agregaciones a mano) y Supabase es nube externa (este lab es
"plataforma propia"). El esquema se escribió a mano en `ingest.py`
(`telemetria,device=lab5 Temperature=…,Humidity=…,Iluminance=… <ts_ns>`) para
que el modelo de datos quede explícito en el repo.

**Grafana está instalado y consultado aparte** (requisito del lab): contenedor
distinto que solo *lee* la TSDB por su API Flux con un token **de solo-lectura**
creado con `influx auth create --read-bucket <ID>`; la ingestión (única
escritora) vive en el contenedor `ingest`. Influx no publica puerto al host.
Cada servicio tiene `mem_limit` y `restart: always` → sobrevive reinicios y no
derriba la VM.

## 4. Regla / alerta por umbral

- **Condición:** media de `Temperature` en los últimos **10 min > 32 °C**
  mantenida **2 min**. El umbral es el techo del rango físico del escenario
  (16–32 °C), así que **no dispara con datos normales** — se fuerza desde el
  publicador, como pide el lab.
- **Acción:** email vía **Brevo SMTP relay**, contact point `brevo-email`
  provisionado como código. Credenciales: usuario = *relay username* que Brevo
  asigna (visible en `GET /v3/account` → `relay.data.userName`), password = la
  **SMTP key** (`xsmtpsib-…`); la API key REST (`xkeysib-…`) no autentica SMTP.
- **Disparo forzado:** `docker compose run -d --no-deps publisher python -u
  python/publisher.py --interval 10 --duration 600 --caliente` fuerza 33–38 °C.
  **Evidencia real (2026-10-17 05:56:30–05:59:30 UTC):** 60 mensajes forzados
  (T=34.9–35.1 °C en `evidencias/forzamiento3.jsonl`), regla en *Firing* y
  `ngalert.sender.router rule_uid=lab5-temp-32 … "Sending alerts to local
  notifier"` **sin errores de autenticación** en el log de Grafana. Captura del
  estado en `evidencias/alerta/` (de la corrida previa, misma regla).

## 5. Ventana de 4 días — bloques y huecos (experimento del hueco)

La toma se ejecutó en **bloques encendido/apagado** para observar el
comportamiento del sistema sin datos (lo solicitado en clase). Datos medidos
desde Influx (`aggregateWindow(every:1h, count)`), UTC:

| # | Estado | Desde (UTC) | Hasta (UTC) | Muestras |
|---|---|---|---|---|
| 1 | 🟢 ON | 2026-10-17 05:00 | 2026-10-17 07:00 | 173 |
| — | 🔴 hueco | 2026-10-17 08:00 | 2026-10-17 13:00 | 0 |
| 2 | 🟢 ON | 2026-10-17 14:00 | 2026-10-18 07:00 | 1 033 |
| — | 🔴 hueco | 2026-10-18 08:00 | 2026-10-18 22:00 | 0 |
| 3 | 🟢 ON | 2026-10-18 23:00 | 2026-10-19 21:00 | 1 302 |
| — | 🔴 hueco | 2026-10-19 22:00 | 2026-10-21 01:00 | 0 |
| 4 | 🟢 ON | 2026-10-21 02:00 | 2026-10-22 05:22 (corte) | 1 677 |
| | **Total** | **ventana 17→22 oct (5 días)** | | **4 185** |

**Lectura:** 4 185 muestras a 60 s ≈ 69.7 h de muestreo efectivo sobre 120 h de
ventana (58 %). Los huecos son reales (no ceros: Influx no inventa puntos); en
Grafana las series se cortan y saltan, el stat "última lectura" se congela en el
último valor previo al apagón y el contador "muestras en la ventana" baja. La
regla de alerta tiene `noDataState: OK` → **no se generan falsas alertas durante
los huecos**. Al volver a encender, nginx + los 5 contenedores + el dashboard
suben solos (`restart: always` + systemd) y la serie **continúa** desde el punto
anterior (verificado tras el reinicio del 17-oct: el último mensaje saltó del
apagón a las 13:31 UTC con el pipeline escribiendo de nuevo).

## 6. Qué falló al instalar (detalle en docs/bitacora.md)

1. **PUBACK de 10 005 ms y desconexiones MQTT**: falta de `loop_start()` en
   paho; sin hilo de red no se procesan PUBACK ni keepalive. La "latencia del
   broker" era del cliente. Fix: `loop_start()` tras conectar.
2. **`hop_ms` = −1.78e15**: dividir nanosegundos entre 1e6 en vez de 1e9.
3. **Token lector Influx**: `--read-only` no existe; `--read-buckets` global es
   rechazado por el query API; se necesita `--read-bucket <ID>`.
4. **Datasource Flux de Grafana**: rechaza basic-auth; el token va en
   `secureJsonData.token`.
5. **Alerta provisionada**: `conditions` del threshold debe ser LISTA y el
   umbral va en `evaluator.params` (`gt: got 0 but need 1`).
6. **`nohup … &` por SSH** cuelga el canal (el wrapper hereda el pipe): usar
   `docker compose run -d`.
7. **Sed sobre `.env` con caracteres no ASCII** corrompió la línea SMTP →
   compose no arrancaba; reescribir por filtrado, no con sed a ciegas.
8. **Pérdida total de la primera VM**: Azure la desasignó por fondos del plan
   estudiante y su **OS disk era temporal (ephemeral)** → se borraron InfluxDB y
   la toma. Mitigación en la VM nueva: disco persistente verificado (`sda` con
   `/boot`), evidencia crítica replicada al repo local, y reconstrucción
   reproducible desde cero en ~20 min (`README`). **Lección: nunca una toma de
   días sobre disco ephemeral.**

## 7. Repo entregable

`docker/docker-compose.yml` + `Dockerfile.python` + provisioning (datasource,
dashboard, regla y contact point) + `python/publisher.py` e `ingest.py` con
`test_python.py` + `dashboard/` (página didáctica) + `tools/` (sync VM por key)
+ este informe + `docs/bitacora.md` + `evidencias/` (jsonl crudos, logs de la
alerta, capturas).

**Entregable imprimible:** `Informe_Lab5_Jose_Tellez_U00060479.pdf` (4 páginas,
con el anexo de evidencias al final). Las imágenes del anexo están además en
`evidencias/` como PNG sueltos (ver `evidencias/README.md`) para poder
revisarlas sin abrir el PDF.

## 8. Recomendaciones

- **Por capa:** aplicar los fixes 1–2 como tests (ya en `test_python.py`);
  versionar el provisioning de Grafana (la alerta es código); medir antes de
  subir servicios (~204 MB de stack real en 892 MB, con límites por contenedor).
- **Por protocolo:** QoS 1 local (PUBACK ≈1 ms) frente a QoS 1 WAN del Lab 4
  (≈115 ms) muestra que el costo vive en la red, no en el broker: la plataforma
  propia es ~100× más rápida end-to-end, pero pierde DPS, gemelo y comandos
  gestionados — ese es el trade-off Cloud↔propia del curso.
- **Operación:** IP pública estática, backup nocturno de Influx y cron de
  DuckDNS (el subdominio caduca a los ~30 días sin actualización).

## 9. Reproducir

`README.md`: 5 comandos desde una VM limpia. Sin secretos en el repo (todo en
`docker/.env`, gitignoreado). Tras la entrega: **rotar la SMTP key de Brevo** y
validar el cron de DuckDNS.

## 10. Anexo de evidencias

Las cuatro evidencias van impresas en el PDF del informe; los PNG originales
están sueltos en `evidencias/` para poder revisarlos sin abrir el PDF
(índice completo en `evidencias/README.md`).

| # | Archivo | Qué demuestra | Sección |
|---|---|---|---|
| Evid. 1 | `evidencias/arquitectura-lab5.png` | Arquitectura real: MQTT → InfluxDB → Grafana dentro de la VM; solo nginx con TLS escucha en público; alerta hacia Brevo SMTP | 2 |
| Evid. 2 | `evidencias/alerta/dashboard-4d-con-datos.png` | Dashboard «Lab 5 — Consola ambiental UNAB (4 días)»: series de temperatura/humedad/iluminancia sobre *Last 4 days*, stats (28.8 °C, 47.3 %, 3 059 muestras) y la alerta > 32 °C rotulada; los tramos rectos son los huecos | 4 y 5 |
| Evid. 3 | `evidencias/pagina-didactica-taller5.png` | Página didáctica `/taller5/`: recorrido de cada mensaje, 5 210 mensajes publicados, PUBACK 0.4 ms, hop broker→ingestor 0.4 ms, `influx_status` 204 y últimos mensajes crudos de 90 B | 3 y 5 |
| Evid. 4 | `evidencias/toma-bloques-huecos.png` | Toma por bloques: 4 bloques de captura (173 · 1 033 · 1 302 · 1 677 muestras) y 3 huecos entre el 17 y el 22 de octubre | 5 |

Además, en crudo: `evidencias/forzamiento3.jsonl` (60 mensajes a 34.9–35.1 °C
que dispararon la regla) y `evidencias/alerta/grafana-alerta-vm2.log`
(`rule_uid=lab5-temp-32` en *Firing*, `Sending alerts to local notifier` sin
errores de autenticación).

