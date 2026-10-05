# Bitácora — Taller 4: AMQP + CoAP vs MQTT hacia Azure IoT Central

**Estudiante:** José Alejandro Téllez Prada
**App IoT Central:** `clima-salones-app-jose.azureiotcentral.com`
**VM:** `vmtalleresjose` (52.237.172.24, North Central US, Ubuntu 24.04)
**Sesiones:** 2026-10-02 → 2026-10-03 (planificación + implementación)

---

## [2026-10-02 ~21:30] Apertura y planificación del Lab 4

- **Qué se hizo:** lectura de la especificación (`laboratorio4.md`, v3: AMQP + tercer
  protocolo + comparación de 3 dispositivos/clientes). Revisión del contexto heredado:
  Lab 2 (SDK), Lab 3 (MQTT explícito, plantilla `consola-unab-ambiental`, variables
  `Temperature`/`Humidity`/`Iluminance`), y el proyecto de 10 devices (patrón REST API
  de IoT Central que le gustó al profesor).
- **Decisiones:**
  - 3 protocolos: **MQTT** (baseline Lab 3) · **AMQP** · **CoAP** (elección del grupo).
  - CoAP no es nativo de IoT Central → arquitectura **gateway propio en la VM**
    (servidor CoAP UDP 5683 + puente a Central). El lab exige mostrar explícitamente
    el componente intermedio, no fingir conexión directa.
  - Devices dedicados por protocolo para no mezclar telemetría.
  - Todo corre en la VM con Python (sin proveedores externos).

## [2026-10-02 21:45] HALLAZGO MAYOR: pérdida de las VMs de la cuenta + Azure Policy

- **Qué pasó:** las VMs anteriores (`57.156.66.112`, `57.156.62.111`) no respondían en
  ningún puerto (verificado por TCP: 22/80/443/8883/5671 = timeout). **Todas las
  máquinas virtuales de la cuenta se perdieron por un error desconocido.**
- **Error al redesplegar:** `RequestDisallowedByAzure` (`InvalidTemplateDeployment`) —
  una **Azure Policy** de la suscripción bloquea desplegar VM+VNet+IP+NSG en
  **Mexico Central** (y Chile Central tampoco está autorizada).
- **Diagnóstico (Cloud Shell):** `az policy assignment list --query "[].parameters"
  --output json` → solo 5 regiones permitidas: `centralus`, `eastus`, `westus3`,
  `northcentralus`, `brazilsouth`.
- **Solución:** el SKU `Standard_B2ats_v2` solo está disponible en **North Central US**
  dentro de las 5 autorizadas → VM creada ahí: `vmtalleresjose` (52.237.172.24).
- **Evidencia completa:** `evidencias/vm_azure_policy_hallazgo.md`.

## [2026-10-02 22:30] HALLAZGO: la app IoT Central fue recreada (plantilla y devices del Lab 3 no existen)

- **Qué pasó:** vía REST API (tokens SAS del usuario) se listaron plantillas y devices
  de `clima-salones-app-jose`: la plantilla `consola-unab-ambiental` y los devices
  `23z8rpgm6s4`/`esp32-wokwi-01` **no existen** (404). La app tiene ahora otras
  plantillas (Hobo MX-100, PhoneAsADevice, sensor calidad del aire) y otros devices.
- **Datos nuevos reales:** `idScope = 0ne0128155B` (antes `0ne0128547D`); el hub vigente
  lo asigna DPS: `iotc-e7f4a710-e390-4518-8432-64b09bb265ca.azure-devices.net`
  (antes `iotc-47a415d3-...`).
- **Solución:** `python/provision_devices.py` recrea la plantilla `consola-unab-ambiental`
  (PUT `/api/deviceTemplates/{id}` con `@type: ["ModelDefinition","DeviceModel"]`,
  capabilityModel como `Interface` con @id distinto — el duplicado de `@id` da 422) y crea
  3 devices dedicados: `mqtt-baseline-01`, `amqp-lab4-01`, `coap-gateway-01`.
- **Notas de API:** la REST API de IoT Central exige prefijo `/api/` y
  `api-version=2022-07-31`; el header `Authorization` va con el token SAS tal cual.
  Las credenciales del device: `GET /api/devices/{id}/credentials` devuelve
  `{idScope, symmetricKey:{primaryKey}}` directamente.

## [2026-10-02 23:00] HALLAZGO: azure-iot-device 2.x YA NO TIENE AMQP

- **Qué pasó:** `IoTHubDeviceClient.create_from_connection_string(cs, transport="Amqp")`
  → `TypeError: Unsupported keyword argument: 'transport'`. Auditoría del paquete
  instalado (2.14.0): **cero menciones de AMQP**; solo `mqtt_pipeline.py` y
  `http_pipeline.py`; depende de `paho-mqtt` (no de `uamqp`). También verificado en el
  wheel de 2.13.0: sin AMQP. Microsoft eliminó el transporte AMQP del SDK de dispositivo
  en la serie 2.x (en 1.x existía vía uamqp).
- **Implicación (fuerte para la comparativa):** la tendencia del SDK es MQTT-only;
  AMQP sobrevive en el plano de servicio (Service Bus/Event Hubs) y en IoT Hub como
  protocolo nativo, pero el SDK de dispositivo moderno ya no lo trae.
- **Solución:** cliente **AMQP 1.0 explícito sobre `uamqp`** (mismo espíritu "abrir la
  caja negra" del Lab 3): SAS token HMAC-SHA256 en memoria (misma fórmula del Lab 3),
  auth CBS (put-token a `$cbs`), link de envío a
  `amqps://{hub}/devices/{id}/messages/events`, medición send→disposition.

## [2026-10-02 23:15] Los 3 clientes implementados y probados en LOCAL

- **`python/common.py`** — generación compartida de las 3 variables (random-walk ±0.5,
  mismos rangos DTDL del Lab 2), payload JSON plano de 1 decimal = **60 bytes**;
  `central_conn_str()` (DPS idempotente con reintentos + cache en `.dps_cache.json`);
  `build_sas_token()` (fórmula Lab 3, compartida por MQTT y AMQP).
- **`python/mqtt_baseline.py`** — paho 1.6 (azure-iot-device fija `paho<2.0`), TLS 8883,
  QoS 1, mide publish→PUBACK. Local: **avg 176.4 ms** (n=4, min 167.6, max 184.7).
- **`python/amqp_sdk.py`** — uamqp 1.6.11, AMQP 1.0/TLS 5671, auth CBS con SAS token.
  Local: handshake completo (TLS+CBS+attach) en el 1er mensaje = **1433 ms**; estado
  estacionario **~165–180 ms**; 100% `SendComplete`, 0 fallos.
- **`python/coap_client.py` + `python/coap_gateway.py`** — aiocoap: nodo constrained
  POSTea JSON a `coap://127.0.0.1:5683/telemetry`; gateway responde **2.04 Changed** y
  reenvía a Central (device `coap-gateway-01`). Local: RTT cliente **avg 174.5 ms**,
  del cual el forwarding a Central es ~172 ms → **el salto CoAP/UDP local es
  sub-milisegundo**; 60 B por datagrama.
- **Errores resueltos en el camino (registrados por ser didácticos):**
  1. `aiocoap.resource.Resource` no tiene `add_resource` en esta versión → usar `Site`.
  2. aiocoap no puede bindear a `0.0.0.0` con su transporte por defecto → `127.0.0.1`.
  3. Gateway sin `load_dotenv()` → KeyError de env vars.
  4. DPS `401` con `mqtt-baseline-01`: el `.env` traía `MQTT_DEVICE_ID=23z8rpgm6s4`
     (device eliminado) — firmaba con key nueva pero ID viejo. Corregido a
     `mqtt-baseline-01`.
  5. Importar `uamqp` + registrarse en DPS en la misma corrida falló 3/3 → aparente
     throttling de DPS ante ráfagas de registros → añadidos **reintentos con backoff**
     y **cache de conn string** en `.dps_cache.json`.
  6. Doble conexión con el mismo device identity (gateway local del smoke test quedó
     vivo en PID 32508 peleándose con el gateway de la VM) → "Unexpected disconnection"
     en el SDK. El proceso local fue matado.

## [2026-10-04 01:00] Diagnóstico del gateway CoAP + corridas formales (sesión 2)

- **Diagnóstico del bug del gateway:** el `ConnectionDroppedError` en bucle NO era
  del código ni del SDK. Causa raíz: el gateway se lanzaba con `nohup ... &` desde una
  sesión SSH interactiva y **el proceso se moría al cerrarse la sesión SSH** (el
  `&` hereda el session leader; al desconectarse SSH, se enviaba SIGHUP y caía). En
  foreground el gateway conecta en ~80 ms y se queda estable (verificado 40 s).
  Verificado también: la identidad duplicada del error #6 ya no existe.
- **Solución aplicada:** `setsid nohup .venv/bin/python -u python/coap_gateway.py ... &
  < /dev/null > log 2>&1` → el gateway **sobrevive el cierre de SSH** y queda estable
  en background (comprobado con una sesión nueva: PID vivo, puente conectado).
- **Corridas formales en la VM (90 s, intervalo 10 s):**
  - MQTT: **9 mensajes, puback avg 114.9 ms** (min 104.0, max 124.3) → `evidencias/mqtt/vm-formal.jsonl`
  - AMQP: **9 mensajes SendComplete, avg 148.9 ms** (1er msg 430.1 ms = handshake
    TLS+CBS+attach; steady ~114.5 ms, min 100.1, max 118.9) → `evidencias/amqp/vm-formal.jsonl`
  - CoAP: gateway en background (setsid) + cliente; **8 mensajes, RTT avg 120.9 ms**,
    8/8 `2.04 Changed`; forwarding del gateway avg 119.0 ms → `evidencias/coap/vm-{client,gateway}-formal.jsonl`
- **Evidencias bajadas a local** con `tools/vm_pull.py` (MQTT/AMQP/CoAP formales + log
  del fallo original `vm-gateway-fail.log`).
- **Gráficas generadas** con `python/python/make_charts.py` → `evidencias/comparativa/`
  (barras, boxplot, serie temporal, bytes, diagrama de arquitectura).
- **Informe:** `informe-lab4.md` creado. Falta: capturas de Central por el usuario y
  revisión final.

## [2026-10-05 04:20→05:00] Sala de control didáctica en vivo + captura de evidencia (sesión 3)

- **Qué se hizo:** dashboard Flask en la VM que muestra los 3 protocolos en vivo y permite
  iniciar/detener cada uno desde el navegador, más un módulo de captura de evidencia para
  el informe. URL pública: **http://iotcentraljose.duckdns.org:8080** (DuckDNS ya resuelve
  a 52.237.172.24; NSG con 80/443/8080 abiertos, verificado por TCP desde fuera).
- **Archivos nuevos:** `dashboard/dashboard.py` (API + vistas), `dashboard/templates/index.html`
  (control room oscuro, canvas puro sin dependencias), `dashboard/templates/informe.html`
  (página imprimible de evidencia), `dashboard/templates/_diagrama.html` (SVG de la
  arquitectura real), `dashboard/hacer_graficas.py` (PNG con matplotlib/Agg) y
  `tools/dash_deploy.py` (sube + instala + arranca con `setsid`).
- **Hallazgos/bugs resueltos en el camino (didácticos):**
  1. **`pkill -f 'dashboard/dashboard.py'` desde el propio SSH se mata a sí mismo:** el
     comando SSH contiene ese texto y `pkill -f` matchea el shell que lo ejecuta. El truco
     `[d]ashboard` tampoco basta si la ruta aparece en otra parte del mismo comando. → se
     para por PID (`evidencias/dashboard.pid` + el que escucha en :8080).
  2. **La petición HTTP se colgaba al lanzar un cliente:** con `subprocess.run(...,
     capture_output=True)` el pipe de salida lo retenía el subshell de fondo de
     `nohup ... &` (que queda vivo como padre del script) → la respuesta no volvía hasta
     matar el script. → `exec setsid <python>` + `Popen` con los fd en `DEVNULL` y
     `start_new_session=True`. Ahora `/api/prueba/iniciar` responde en ~4 s.
  3. **Canvas en blanco/escalado:** `prep()` usaba el atributo `canvas.height` (150 por
     defecto) en vez del alto CSS → las gráficas se dibujaban a 150 px y se estiraban. →
     `getBoundingClientRect().height`.
  4. **`matplotlib 3.11`** ya no acepta `boxplot(labels=...)` → `tick_labels=` con fallback.
  5. **Boxplot ilegible:** el 1er mensaje AMQP (~500 ms de handshake) aplastaba la escala de
     todos los demás → se excluye de esa figura y se anota en el título.
  6. **Intervalo "?"** en el reporte cuando la corrida no se lanzó desde el panel → se
     estima el intervalo real por la mediana de las diferencias de timestamp.
- **Protección:** las acciones de escritura (iniciar/detener/capturar) exigen la clave
  `DASH_KEY` (header `X-Dash-Key` o `?key=`); el valor vive solo en el `.env` de la VM.
- **Verificado desde fuera (no solo local):** `GET /` 200 (33 KB), `/api/estado` 200 con los
  3 protocolos, `POST .../detener` 401 sin clave y 200 con clave, `/api/evidencia` 200 con
  PNG generados, `/api/paquete.zip` 200 (36 archivos) y `/informe` 200 con las 4 gráficas.

## [2026-10-05 05:00→05:40] HTTPS en el dominio + la página didáctica (sesión 4)

- **Dominio con HTTPS real:** `https://iotcentraljose.duckdns.org/` (antes `http://…:8080`).
  - **nginx** (apt) como reverse proxy: `:80` → 301 a `:443`, y `:443` → `127.0.0.1:8080`.
  - Certificado **Let's Encrypt** con `certbot --nginx` (reto HTTP-01 por el puerto 80, sin
    necesidad del token de DuckDNS). Vence 2027-01-03 y queda con **renovación automática**
    (`certbot.timer`, revisa dos veces al día).
  - La app pasó de «Flask dev server con setsid» a **gunicorn (2 workers) con servicio
    systemd** `taller4-dashboard`: arranca sola, se reinicia si se cae y se opera con
    `systemctl status/restart taller4-dashboard` (+ logs en `journalctl -u taller4-dashboard`).
  - El puerto **8080 ya no está expuesto a Internet**: gunicorn escucha solo en `127.0.0.1` y
    la única entrada pública es nginx (80/443). Verificado desde fuera: `:8080` cerrado.
  - Scripts: `tools/vm_https.py` (instala y configura nginx + certbot y verifica el resultado)
    y `tools/dash_deploy.py` actualizado (sube, instala flask/matplotlib/gunicorn y reinicia el
    servicio systemd).
- **Página más didáctica** (para *ver* cómo viaja el mensaje, no solo leerlo):
  - **Carrera de latencia**: un punto por mensaje real, un carril por protocolo (VM → IoT
    Central), con el ms real al llegar; los tres sobre la misma escala relativa.
  - **Pila de protocolos** por cada uno (aplicación / sesión-link / transporte / seguridad /
    red); CoAP muestra además el **puente** del gateway.
  - **Peso de cada mensaje**: 60 B de datos frente a la cabecera fija (MQTT 2 B, AMQP 8 B,
    CoAP 4 B) y la nota del costo real (handshake TLS+CBS en AMQP; topic y tramas TCP/TLS en MQTT).
  - **Secuencia real del último intercambio** con los tiempos medidos (PUBACK / disposition /
    RTT + forwarding) actualizándose en vivo.
  - **Qué mide cada KPI**, **cuándo usar cada protocolo** y un **glosario de 12 términos**
    (QoS 1, topic, link/créditos, CBS, disposition, CON y 2.04 Changed, UDP vs TCP, gateway,
    SAS, handshake TLS, datagrama, device/plantilla).
- **Seguridad:** el panel solo es accesible por HTTPS y las acciones de escritura siguen
  exigiendo `DASH_KEY` (`X-Dash-Key`).

## [2026-10-05 05:30→06:00] Robustez: ¿aguanta la VM pequeña hasta diciembre? (sesión 5)

**Medición real** (VM `Standard_B2ats_v2`: 2 vCPU, 896 MB RAM, 29 GB disco):

| Recurso | Medido |
|---|---|
| RAM | 896 MB totales · ~580 en uso · ~317 disponibles · **swap: 0** (antes) |
| CPU | load 0.06–0.10 sobre 2 vCPU (~5 %) |
| Disco | 3.1 GB usados · 25 GB libres |
| App | dashboard (gunicorn, 2 workers) ≈ **111 MB** (`MemoryCurrent`); cada cliente 20–42 MB |
| Crecimiento de logs | **~6 MB/día por protocolo** (intervalo 3 s) ≈ 18–25 MB/día en total |
| journald | 60 MB (sin tope: el valor por defecto es 10 % del disco = 2.9 GB) |

**Dos problemas reales encontrados y arreglados:**

1. **El conteo de líneas era O(tamaño) en cada refresco.** `contar_lineas()` recontaba el archivo
   completo cada 2.5 s porque el archivo siempre cambia; con semanas de log (cientos de MB) eso
   era leer cientos de MB cada 2.5 s **por protocolo** → CPU y disco al piso.
   → Ahora cuenta **incrementalmente**: solo los bytes nuevos desde la última cuenta, y hace
   recuento completo si detecta que el archivo se truncó.
2. **Un cliente caído dejaba la demo a medias.** Son procesos que viven semanas; AMQP sobre
   `uamqp` **no tolera una caída de red** (la excepción mata el proceso, hallazgo nuevo) y
   cualquiera puede tener una fuga de memoria.
   → **Vigilante** dentro del dashboard (hilo con `flock`, lo corre un solo worker):
   - si un protocolo marcado como activo no responde → lo relanza **sin borrar** el log
     (la corrida y su evidencia continúan, no se pierde la captura);
   - si el RSS del protocolo supera 260 MB → lo reinicia (contra fugas);
   - si el gateway CoAP no está escuchando → lo vuelve a levantar;
   - **rotación**: cualquier `live*.jsonl` mayor a 40 MB se vacía (los scripts escriben con
     `O_APPEND`, así que siguen escribiendo al final del archivo);
   - deja bitácora en `evidencias/autoreinicio.log` y el nº de reinicios aparece en la tarjeta;
   - respeta las acciones manuales (ventana de 25 s) y tiene backoff de 60 s para no reiniciar en bucle.
   - **Probado en vivo:** maté el cliente AMQP y el gateway CoAP; el vigilante los levantó solo
     (`reinicio amqp: proceso caído (nº 1, sigue la corrida)`) y el contador siguió **789 → 801**.

**Endurecimiento del servidor** (`tools/vm_robustez.py`, idempotente):

- **Swap de 2 GB** (y en `/etc/fstab`): sin swap, un pico de matplotlib (~120 MB) podía despertar
  al OOM killer, que mata cualquier proceso —incluido uno de los clientes—. Además `vm.swappiness=10`.
- **journald limitado a 200 MB** con retención de 1 mes (antes podía llegar a 2.9 GB).
- `MemoryMax=450M` + `MemorySwapMax=1G` al servicio: si la app se dispara, systemd la contiene en
  vez de dejar sin memoria a toda la máquina.
- Verificado: `logrotate` de nginx activo y `unattended-upgrades` con `Automatic-Reboot=false`
  (no habrá reinicios sorpresa; y si los hubiera, todo vuelve solo por systemd + fstab).

**Riesgos que NO dependen de la VM (a vigilar hasta diciembre):**

1. **IP pública dinámica:** si la VM se **desasigna** (stop desde el portal, o se agota el crédito
   de Azure for Students) la IP puede cambiar y DuckDNS quedaría apuntando mal. Mientras siga
   encendida, la IP no cambia. *Este es el riesgo número uno para las demos.*
2. **DuckDNS elimina subdominios inactivos:** su política borra el dominio tras ~30 días sin
   actualización. Conviene un cron diario con el token:
   `curl "https://www.duckdns.org/update?domains=iotcentraljose&token=<TOKEN>"`.
3. **Certificado TLS:** se renueva solo (`certbot.timer`; probado con `certbot renew --dry-run`).

**Tercer hallazgo: un redespliegue cortaba la corrida.** Los clientes quedaban dentro del *cgroup*
del servicio, así que `systemctl restart taller4-dashboard` los mataba a los tres (y el vigilante
tenía que levantarlos). → `KillMode=process` en la unidad: ahora actualizar el dashboard **no toca**
los clientes. Y de paso: el vigilante ahora reintenta el candado cada 20 s y hace su primera pasada
a los 3 s (antes podía tardar más de un minuto en tomar el relevo tras un reinicio del servicio).

**Prueba de reinicio de la VM (`tools/vm_reboot_test.py`), resultado real:**

| Comprobación | Resultado |
|---|---|
| SSH vuelve | **18 s** |
| nginx y taller4-dashboard | `active` y `enabled` (arrancan solos) |
| swap | 2 GB montados (está en `/etc/fstab`) |
| Protocolos | los 3 **relanzados solos** por el vigilante y publicando otra vez |
| Contadores | **continuaron** (mqtt 1039→1052, amqp 1032→1035, coap 790→800): no se perdió la corrida |
| HTTPS desde fuera | 200 |
| Certificado | `certbot renew --dry-run` → *«all simulated renewals succeeded»* |

**Conclusión:** con esto la VM aguanta de sobra hasta diciembre y más para demos de clase:
el disco crece ~25 MB/día sobre 23 GB libres, la memoria queda con ~300 MB de holgura más 2 GB de
swap, y lo que se caiga (o un reinicio completo de la máquina) se levanta solo en menos de un minuto.

## Estado de evidencias (local `taller_4_iot/evidencias/`)

- **Preparado:** `python3-venv`/`pip` instalados (sudo -S con contraseña), código
  subido con `tools/vm_push.py` (SFTP), `.env` en la VM (chmod 600), venv creado,
  dependencias OK (`azure-iot-device`, `uamqp`, `paho`, `aiocoap`).
- **MQTT baseline en VM: OK.** 3 mensajes, puback **avg 117.2 ms** (min 113.7, max
  121.2) — más rápido que local (117 vs 176 ms) por proximidad de red Azure.
  Evidencia: `evidencias/mqtt/vm-run.jsonl` (en la VM).
- **AMQP en VM: OK.** 3 mensajes `SendComplete`, steady **~114–117 ms** (1er msg 456 ms
  con handshake TLS+CBS+attach). Evidencia: `evidencias/amqp/vm-run.jsonl` (en la VM).
- **CoAP en VM: PARCIAL** — el gateway se lanza y corre, pero su puente MQTT entra en
  bucle de `ConnectionDroppedError` cuando corre en background (`setsid nohup`), y el
  proceso llegó a morir. En LOCAL el mismo código funciona perfecto. Pendiente de
  diagnóstico (ver HANDOFF.md): correr en foreground con `-u`, revisar si hay doble
  identidad, considerar `keep_alive` del SDK. Los prints `[DPS]/[GW]` no aparecieron en
  el log de la VM (stdout buffering; con `-u` tampoco llegaron a imprimirse).

## Estado de evidencias (local `taller_4_iot/evidencias/`)

| Archivo | Contenido |
|---|---|
| `vm_azure_policy_hallazgo.md` | Hallazgo VMs perdidas + Azure Policy + solución |
| `mqtt/run.jsonl` | MQTT local (puback por mensaje, avg 176.4 ms) |
| `amqp/run.jsonl` | AMQP local (ack + outcomes; 1er msg 1433 ms handshake) |
| `coap/client.jsonl` + `coap/gateway.jsonl` | CoAP local (RTT cliente + forwarding) |
| `mqtt/vm-formal.jsonl` | MQTT VM formal (9 msgs, avg 114.9 ms) |
| `amqp/vm-formal.jsonl` | AMQP VM formal (9 msgs, avg 148.9 ms; steady 114.5 ms) |
| `coap/vm-client-formal.jsonl` + `coap/vm-gw-formal.jsonl` | CoAP VM formal (RTT 120.9 ms + forwarding 119.0 ms) |
| `coap/vm-gateway-fail.log` | Log del fallo original del gateway (bucle ConnectionDroppedError) |
| `comparativa/*.png` | Gráficas matplotlib (barras, boxplot, serie, bytes, arquitectura) |

## Pendiente

1. ✅ Gateway CoAP estabilizado en la VM (causa: proceso en background moría con el cierre de SSH → `setsid`). Corridas formales 90 s completadas.
2. ✅ Evidencias de la VM bajadas a local (`tools/vm_pull.py`).
3. ✅ Corridas formales MQTT (114.9 ms) / AMQP (148.9 ms) / CoAP (120.9 ms) en la VM.
4. ⏳ **Capturas del usuario** en IoT Central Data explorer (telemetría de los 3 devices).
5. ✅ Tabla comparativa + gráficas (`evidencias/comparativa/*.png`).
6. ✅ Informe (`informe-lab4.md`) creado.
