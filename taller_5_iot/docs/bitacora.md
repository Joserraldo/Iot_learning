# Bitácora — Laboratorio 5: plataforma propia (MQTT → InfluxDB → Grafana)

**Autor:** José Alejandro Téllez Prada (u00060479) · **Fecha sesión 1:** 2026-10-07/08
**VM:** misma del Lab 4 (`52.237.172.24`, Ubuntu, 896 MB + 2 GB swap, mismo `.pem`
y credenciales del `.env` del taller 4) · **Dominio:** mismo DuckDNS
`iotcentraljose.duckdns.org`, TLS Let's Encrypt ya existente.

---

## 1. Plan y decisión de arquitectura

Objetivos del lab: instalar en la VM el stack propio (protocolo + TSDB + Grafana
aparted e instalado en docker compose, definir una regla de alerta por umbral y
dejarla evidenciada, y dejar corriendo la toma de 4 días.

| Elección | Descarte y por qué |
|---|---|
| **MQTT + Mosquitto** | El lab deja elegir uno de MQTT/AMQP/CoAP. AMQP/CoAP en plataforma propia obligan a RabbitMQ o a recrear el gateway del Lab 4; MQTT tiene el broker canónico en Docker (eclipse-mosquitto) y QoS 1 da una evidencia medible por mensaje (PUBACK), continuando lo aprendido en los Labs 3–4. EMQX se descartó por peso (Erlang, dashboard propio) para un salón de clase. |
| **InfluxDB 2.7** | Mongo: base de documentos, no TSDB (tocaba diseñar esquema y ventanas de agregación a mano, duplicando lo que una TSDB da nativa). Supabase/Postgres cloud: es servicio externo y el lab dice plataforma propia en la VM. Timescale/QuestDB son válidas; Influx gana por la integración Flux nativa con Grafana y porque el bucket+token modela bien "Grafana aislado de la BD". |
| **Grafana OSS 11.2** | Único candidato serio para visualización+alertas self-hosted. Se provisiona datasource, dashboard y regla de alerta como CÓDIGO en el compose, para que el stack sea reproducible (rubrica 25%). |
| **Alerta >32 °C → email Brevo** | Conexión directa con el Lab 3 (allí la regla vivía en IoT Central; aquí en Grafana). El umbral está fuera del rango físico del escenario (16–32 °C) a propósito: la alerta nunca dispara sola y se fuerza con `--caliente`, cumpliendo "forzar el valor desde el publicador". Brevo = SMTP (no depende de servicios externos salvo el envío de correo). |
| **Docker Compose + subruta /taller5** | docker es "el camino preferido" del enunciado. El servidor SÍ tiene capacidad: medido, el stack consume ~204 MB (límites totales 832 MB, real <500) sobre 896 MB + 2 GB de swap ya endurecidos en el Lab 4; el taller 4 queda en `/` y el 5 en `/taller5/` + Grafana en `/taller5/grafana/` (sub-path nativo de Grafana). No se movió el taller 4 a `/taller4`: sus plantillas usan rutas absolutas y romper la sala viva del Lab 4 por cosmética es riesgo sin beneficio. |

**Diagrama final:** publicador → mosquitto (1883, solo red interna) → ingestor
(sube línea Influx + mide hop) → influxdb (bucket `telemetria`, ns, puerto SIN
publicar) → Grafana (datasource Flux con token SOLO-LECTURA, contacto email
Brevo, regla `lab5-temp-32`) → navegador solo vía nginx con TLS. Página
didáctica Flask en `:8090` loopback. Ningún servicio nuevo escucha en el público.

## 2. Sesión 1 — despliegue (2026-10-07 noche)

### Instalación de Docker
La VM no tenía Docker (el Lab 4 corrió procesos con venv). Instalado con
`curl -fsSL https://get.docker.com | sh` (sudo con la contraseña por stdin,
pitfall del skill para no dejarla en `ps`), y `usermod -aG docker azureuser`.
Verificado: `docker run --rm hello-world` → `Hello from Docker`.

### Código (TDD aplicado)
Primero el test `python/test_python.py` (payload, modo caliente, línea Influx)
— fallo real con `ModuleNotFoundError`, luego `OK 3/3`. Después publisher.py e
ingest.py hasta pasar.

### Errores de la corrida (todos reales, todos con causa raíz)

1. **`puback_ms` = 10005 ms y desconexiones del broker.** Síntoma: el
   publicador imprimía 10 s de latencia y el broker "Client … exceeded
   timeout". Causa raíz: paho-mqtt exige un loop de red; sin
   `client.loop_start()` el PUBLISH QoS1 se encola y nadie procesa el PUBACK
   ni el keepalive — `wait_for_publish(timeout=10)` devolvía el timeout y se
   registraba como latencia. Fix: `loop_start()` tras conectar, idem en el
   ingestor (que además nunca recibía con el main dormido). Lección didáctica:
   el LAB 3 habló de "abrir la caja negra del SDK"; aquí abrimos la del cliente
   MQTT: la latencia medida era la de nuestra propia arquitectura de hilos, no
   la del broker.
2. **`hop_ms` = −1.78e15.** El ts del payload está en NANOsegundos y se dividió
   por 1e6 (µs). Fix: `/1e9`. El signo negativo delatava un error de unidades,
   no de reloj.
3. **CLI influx `-o` ambiguo**: `influx query … -o csv` choca porque `-o` es
   alias de `--org`. Usar `--org unab` a secas y formato por defecto.
4. **Token lector**: `influx auth create --read-only` no existe; el token con
   `--read-buckets` global dio *unauthorized* al consultar. Lo que funciona:
   `--read-bucket <ID>` (el ID se saca de `influx bucket list`). Script
   definitivo: `docker/crear_token_reader.sh`.
5. **Datasource Influx en Grafana**: con `basicAuth` el query devolvía
   "plugin.downstreamError". El plugin Flux espera el token en
   `secureJsonData.token`, no basic auth. Corregido el provisioning → query
   200 OK con frames.
6. **Regla de alerta provisionada**: el evaluador de Grafana rechazó el YAML
   dos veces ("cannot unmarshal object into []ThresholdConditionJSON" y
   "gt: got 0 but need 1"). Formato correcto: `type: threshold` con
   `conditions` como LISTA y el umbral en `evaluator.params:[32]`. Con eso el
   scheduler evaluó la regla sin errores.
7. **Sed con la clave SMTP**: un `sed` con comodines sobre un `.env` con
   caracteres no-ASCII dejó la línea corrupta (`BREVO_…`) y docker compose no
   arrancaba. Recuperado filtrando líneas con awk+grep, no con sed a ciegas.
   (También: `UID` es variable readonly en bash → renombrar a `CPID`.)
8. **`nohup … &` colgó el SSH** (pitfall documentado del Lab 4): el `&` aplica
   al `&&` completo y el wrapper mantiene el pipe abierto → timeout en el
   canal. Para procesos detached: `docker compose run -d` (recomendado) o
   `setsid` con fds redirigidos.

### Alerta: disparo forzado + email (RESUELTO)
Corrida `--caliente --interval 10 --duration 600`: el log
`evidencias/forzamiento.jsonl` quedó con T=33–38 °C y el log de Grafana muestra
el ciclo completo: regla evaluada → *Firing* → `Sending alerts to local notifier`
(t=00:50:30). El contacto email falló con `535 Authentication failed`. **Causa
raíz (error nuestro, no de Brevo):** usamos como usuario SMTP el email de la
cuenta (`jtellez312@unab.edu.co`), pero Brevo autientica con un **usuario relay
asignado** — se lee en `GET https://api.brevo.com/v3/account` →
`relay.data.userName` (nuestro: `b8cab8001@smtp-brevo.com`), siempre con la
**SMTP key** (`xsmtpsib-…`, no la API key REST `xkeysib-…`). Con ese par, login
`LOGIN_OK` y el FROM puede seguir siendo el correo propio. Nota para el informe:
la regla es media móvil de 10 min + `for: 2m`, así que el forzamiento debe durar
~10 min para llenar la ventana.

### Toma de 4 días
Reinicié los jsonl y re-arranqué publisher/ingest a las **23:21 UTC del
2026-10-07** para que la toma inicie limpia y con ts reales (cadencia 60 s →
~1 440 muestras/día → ~5 760 al corte). Corte propuesto: **2026-10-11 23:30
UTC** (sesión 2). Hasta ahora sin huecos (vigilar tras el reboot).

### Durabilidad
- `restart: always` en los 5 servicios + systemd `taller5-dashboard` (activo) +
  nginx ya systemd-enabled del Lab 4. **Prueba de reboot ejecutada
  (2026-10-08 00:58 UTC): a la primera** — up 0 min, los 5 contenedores vivos,
  `taller4-dashboard`/`taller5-dashboard`/`nginx`/`docker` `active`, RAM libre
  410 MB, y la toma reanudó escribiendo (`influx_status: 204`). URLs externas
  verificadas tras el reboot: `/` 200 (Lab 4 intacto), `/taller5/` 200,
  `/taller5/grafana/api/health` 200. Nota: el seq de los jsonl reinicia en 1
  tras cada arranque del publicador (el contador es por proceso; los `.jsonl`
  se abren en modo append y la serie histórica de la TSDB no se toca).
- DuckDNS: el subdominio se pierde tras ~30 días sin actualizar. **PENDIENTE:
  montar cron diario con el token** (mismo riesgo que el Lab 4; token en
  duckdns.org).

## 3. INCIDENTE: pérdida de la VM original + re-deploy en VM nueva (2026-10-16/17)

**Qué pasó (causa raíz documentada, criterio de rúbrica "qué falló"):** la VM
original (`52.237.172.24`) apareció como *"Se detuvo (desasignada)"* en el
portal, con aviso de gasto excesivo de fondos del plan estudiante. Su OS disk
era **temporal (ephemeral)**: Azure borra esos discos al desasignar/eliminar, y
con ellos se fue InfluxDB, los volumenes y la toma de 4 días (sobrevivieron los
jsonl y la evidencia de la alerta ya descargados al repo local). **Lección: una
VM de plan estudiante con disco temporal no sobrevive un deallocation — por eso
esta vez blindamos.**

**Re-deploy (2026-10-16/17):** VM nueva `vmjosesiotcentral` (`52.159.94.196`,
Ubuntu 24.04, misma 892 MB). DuckDNS re-apuntado
(`success: ... updated to 52.159.94.196`). El NSG nuevo solo abría 22 → reglas
80/443 agregadas manualmente en el portal (Let's Encrypt fallaba con "challenges
failed" hasta que se abrieron). Reconstrucción casi idéntica al Lab 5 original
pero con acceso por key (`.pem`, las tools `vmexec/vmsudo/vm_sync` ahora
soportan `VM_KEY`), venv propio del taller 5 (ya no el del taller 4), site nginx
nuevo (en esta VM no hay taller 4: la raíz `301` a `/taller5/`), certbot con el
mismo dominio y renovación automática (`certbot.timer`, expira 2027-01-15).

**Blindaje aplicado a la toma nueva:**
- Snapshot del disco de la VM (cuidado en el portal).
- Cron DuckDNS diario para que el subdominio no caduque a los 30 días
  (mismo riesgo perpetuo del Lab 4). [token: en duckdns.org; cron colgado SI el
  token se provee]
- **Nueva fecha de inicio de la toma: 2026-10-17T04:51:50Z** (cadencia 60 s).
  Corte previsto: **2026-10-21 ~05:30 UTC**. Huecos: ninguno hasta ahora
  (reinicio de jsonl deliberado para que la toma inicie limpia, como la primera).

## 4. Experimento del hueco (bloques encendido/apagado)

Por indicación del profesor, la toma se llevó en **bloques** para observar el
comportamiento del sistema sin datos (huecos). Medición desde Influx
(`aggregateWindow(every:1h, count)`), UTC:

| # | Estado | Desde | Hasta | Muestras |
|---|---|---|---|---|
| 1 | ON | 2026-10-17 05:00 | 2026-10-17 07:00 | 173 |
| — | OFF | 2026-10-17 08:00 | 2026-10-17 13:00 | 0 |
| 2 | ON | 2026-10-17 14:00 | 2026-10-18 07:00 | 1 033 |
| — | OFF | 2026-10-18 08:00 | 2026-10-18 22:00 | 0 |
| 3 | ON | 2026-10-18 23:00 | 2026-10-19 21:00 | 1 302 |
| — | OFF | 2026-10-19 22:00 | 2026-10-21 01:00 | 0 |
| 4 | ON | 2026-10-21 02:00 | 2026-10-22 05:22 (corte) | 1 677 |

Total 4 185 muestras ≈ 69.7 h de muestreo sobre 120 h de ventana (58 %).

**Qué se observó en cada hueco (para el informe):**
- Grafana corta la línea (Influx no inventa puntos; no hay ceros).
- El stat `last()` se congela en el último valor antes del apagón; el contador
  de "muestras en la ventana" baja.
- La alerta NO dispara por falta de datos (`noDataState: OK`) → sin correos
  falsos durante el hueco.
- Al encender: nginx + 5 contenedores + dashboard suben solos
  (`restart: always` + systemd); la serie continúa donde quedó. Verificado el
  17-oct: tras el reinicio, el último mensaje pasó del apagón a 13:31 UTC y el
  pipeline siguió escribiendo (`influx_status: 204`).

**Alerta disparada en esta VM:** forzamiento3 del 17-oct (60 msgs, T=34.9–35.1
°C) → Firing 05:56:30–05:59:30 UTC, `Sending alerts to local notifier` sin
errores. Evidencia: `evidencias/forzamiento3.jsonl` +
`evidencias/alerta/grafana-alerta-vm2.log`.

## 5. Pendientes para la sesión 2 (día 4 de toma)

1. ~~SMTP key válida de Brevo~~ **RESUELTO**: usuario relay `b8cab…@smtp-brevo.com`
   + SMTP key `xsmtpsib-…` → login OK y alerta notificando sin errores
   (`evidencias/alerta/grafana-alerta-final.log`, `forzamiento2.jsonl` con
   T>32). Confirmar visualmente el correo en la bandeja de jtellez312@unab.edu.co
   (carpeta spam también) y capturarla a `evidencias/alerta/`.
2. Capturas del dashboard con la ventana de 4 días al corte (11-oct ~23:30 UTC).
3. Que un compañero lea el dashboard sin explicación (cierre de sesión 2 del lab).
4. Rotar la SMTP key que circuló en chat + recordatorio en el informe.
5. Completar `informe-lab5.md` con la fecha de corte real y el hueco medido.

## 6. Cierre de la toma y entrega (2026-10-22)

**Corte de la toma:** 2026-10-22 05:22 UTC, sobre una ventana de 5 días
(17-oct 04:51 UTC → 22-oct 05:22 UTC) con 4 bloques ON y 3 huecos: 4 185
muestras ≈ 69.7 h de muestreo efectivo sobre 120 h (58 %). La toma se hizo a
bloques **por indicación del profesor**, para poder observar el sistema sin
datos; lo que se aprendió de cada hueco está en la sección 4.

**Lo que se entrega:**

| Pieza | Archivo | Nota |
|---|---|---|
| Informe final (Markdown) | `informe-lab5.md` | 10 secciones + anexo de evidencias |
| Informe final (PDF imprimible) | `Informe_Lab5_Jose_Tellez_U00060479.pdf` | 4 páginas, con el anexo gráfico al final |
| Anexo gráfico (4 PNG) | `evidencias/arquitectura-lab5.png`, `evidencias/alerta/dashboard-4d-con-datos.png`, `evidencias/pagina-didactica-taller5.png`, `evidencias/toma-bloques-huecos.png` | Son las mismas imágenes que van incrustadas en el PDF, extraídas sin recompresión |
| Índice de evidencias | `evidencias/README.md` | Evid. 1–4 + logs crudos (jsonl/log) que respaldan cada medición |
| Bitácora | `docs/bitacora.md` | Este diario: decisiones, errores reales, incidente de la VM y cierre |
| Reproducibilidad | `README.md`, `docker/`, `python/`, `tools/` | 5 comandos desde una VM limpia; sin secretos en git |

**Pendientes que quedan abiertos para después de la entrega** (no bloquean el
lab): rotar la SMTP key de Brevo (circuló en un chat), montar/verificar el
cron de DuckDNS y montar el backup nocturno de InfluxDB. También quedó sin
hacer la prueba de "que un compañero lea el dashboard sin explicación"
(pendiente 3 de la sección 5).

**Corrección de autoría:** el nombre del autor en los documentos de este
taller figuraba como "José Andrés Téllez Rangel"; el correcto, coherente con
los talleres 1–4 y con el PDF del informe, es **José Alejandro Téllez Prada**
(u00060479). Ajustado en `informe-lab5.md` y en la cabecera de esta bitácora.
