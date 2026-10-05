# Informe Lab 4 — AMQP + tercer protocolo (CoAP) vs MQTT hacia IoT Central

**Autor:** José Alejandro Téllez Prada
**Materia:** IoT + Cloud + Sistemas Distribuidos (Lab 4 · v3)
**App IoT Central:** `clima-salones-app-jose` · **VM:** `vmtalleresjose` (52.237.172.24, North Central US)

---

## 1. Rol de AMQP en Azure y por qué un tercer protocolo (CoAP)

AMQP 1.0 es el protocolo de mensajería del plano de servicio de Azure (Service Bus,
Event Hubs) y uno de los transportes nativos de IoT Hub/IoT Central (puerto 5671).
A diferencia del pub/sub ligero de MQTT, AMQP aporta sesiones, links con
credit-based flow y disposiciones de entrega explícitas.

**Hallazgo clave (documentado en bitácora):** el SDK `azure-iot-device` 2.x **ya no
incluye transporte AMQP** (v2.14.0 auditado: solo MQTT+HTTP, depende de `paho-mqtt`).
Por eso este lab usó un cliente **AMQP 1.0 explícito sobre `uamqp`** (mismo espíritu
"abrir la caja negra" del Lab 3): SAS token HMAC-SHA256 en memoria, auth CBS
(`put-token` a `$cbs`), link de envío a `amqps://{hub}/devices/{id}/messages/events`.

Como tercer protocolo se eligió **CoAP (RFC 7252)**: UDP, bajo overhead, pensado para
constrained devices — contraste directo con los dos TCP/TLS. CoAP no es nativo de IoT
Central, así que se implementó un **gateway propio en la VM**: servidor CoAP UDP 5683
+ puente MQTT a Central (device `coap-gateway-01`). No se finge conexión directa.

| | MQTT | AMQP | CoAP |
|---|---|---|---|
| **Device/cliente** | `mqtt-baseline-01` (paho, explícito) | `amqp-lab4-01` (uamqp, explícito) | nodo `coap_client.py` + gateway `coap-gateway-01` |
| **Dónde corre** | VM | VM | VM (cliente + gateway) |
| **Endpoint destino** | hub IoT Central (`iotc-e7f4…-azure-devices.net`) | idem | gateway local UDP 5683 → puente MQTT → Central |
| **Puerto** | 8883 | 5671 | UDP 5683 (CoAP) / 8883 (puente) |
| **TCP/UDP/WS** | TCP | TCP | UDP (CoAP) + TCP (puente) |
| **TLS** | TLS 1.2/1.3 | TLS | no en el salto CoAP; TLS en el puente |
| **Variables** | Temperature, Humidity, Iluminance | idem | idem |
| **Formato** | JSON plano 60 B | JSON plano 60 B | JSON plano 60 B |

## 2. Evidencia de funcionamiento

Las corridas formales (90 s, intervalo 10 s) se ejecutaron en la VM. Resumen de las
métricas medidas (evidencias crudas en `evidencias/`, gráficas en `evidencias/comparativa/`):

| Protocolo | n | Avg ack | Min | Max | Outliers/handshake | Evidencia |
|---|---|---|---|---|---|---|
| MQTT (VM formal) | 9 | **114.9 ms** | 104.0 | 124.3 | — | `evidencias/mqtt/vm-formal.jsonl` |
| AMQP (VM formal) | 9 | **148.9 ms** | 100.1 | 430.1 | 1er msg = 430.1 ms (handshake TLS+CBS+attach) | `evidencias/amqp/vm-formal.jsonl` |
| AMQP steady | 8 | ~114.5 ms | 100.1 | 118.9 | excluyendo 1er msg | idem |
| CoAP cliente (VM) | 8 | **120.9 ms** (RTT) | 110.7 | 127.6 | — | `evidencias/coap/vm-client-formal.jsonl` |
| CoAP gateway forwarding | 8 | **119.0 ms** | 109.1 | 126.1 | — | `evidencias/coap/vm-gw-formal.jsonl` |
| Local (referencia) | MQTT 4 / AMQP 4 / CoAP 3 | 176.4 / 175.0 / 174.5 ms | | | AMQP local 1er msg 1433 ms | `evidencias/{mqtt,amqp,coap}/*.jsonl` |

**AMQP en Central:** 9/9 `MessageState.SendComplete`, 0 fallos. Las 3 variables
llegaron a la app (visible en Data explorer del device `amqp-lab4-01`).
**CoAP demostrable:** 8/8 datagramas respondidos `2.04 Changed`; el gateway reenvió
los 8 a Central con ack de puente ~119 ms. El salto CoAP/UDP es sub-milisegundo.

## 3. Tabla comparativa (teoría vs observado)

| Criterio | MQTT | AMQP | CoAP |
|---|---|---|---|
| Modelo | pub/sub, topic | peer-to-peer (links) | request/response (CON) |
| Fiabilidad observada | PUBACK QoS1, 100% | disposition `SendComplete`, 100% | 2.04 Changed + retransmisión CON |
| Latencia observada (VM) | 114.9 ms | 148.9 ms (steady 114.5 ms) | 120.9 ms RTT |
| Reconexión | paho reconnect (manual) | uamqp client persistente | gateway con SDK auto-reconnect |
| Overhead | header MQTT pequeño + TCP+TLS | handshake pesado (TLS+CBS+attach ≈ 430 ms) | header CoAP mínimo + UDP sin TLS |
| Firewall/NAT | 8883 a veces bloqueado | 5671/443 (AMQP-WS) | UDP 5683 suele pasar, sin garantía |
| Microcontrolador | ESP32 OK (paho/Arduino) | poco usado en MCU | ideal constrained (RFC 7252) |
| Debug | muy fácil (mosquitto/Wireshark) | medio (frames AMQP) | medio-fácil (mensajes pequeños) |
| Integración Central | nativa | nativa | **requiere gateway propio** |
| Caso de uso ideal | telemetría ligera de sensores | mensajería entre servicios Azure | sensor constrained en red local |

## 4. Recomendaciones por capa

- **Dispositivo (ESP32/Wokwi futuro):** MQTT — soporte maduro en MCU, QoS1, debug fácil.
  CoAP solo si el nodo es muy constrained y hay un gateway propio.
- **Entre servicios Azure / plataforma propia (Labs 5–8):** AMQP (Service Bus/Event
  Hubs) — sesiones, créditos y garantías de entrega que MQTT no tiene.
- **Quedarse con 2 protocolos:** MQTT + AMQP — cubren dispositivo→nube y servicio→servicio;
  CoAP queda como opción para el borde constrained.

## 5. Archivos y evidencias

- Scripts: `python/mqtt_baseline.py`, `python/amqp_sdk.py`, `python/coap_client.py`,
  `python/coap_gateway.py`, `python/common.py`, `python/provision_devices.py`.
- Herramientas VM: `tools/vm_push.py`, `tools/vm_pull.py`, `tools/vmexec.py`, `tools/dash_deploy.py`.
- Evidencias: `evidencias/{mqtt,amqp,coap}/*.jsonl` (local + VM formal) y
  `evidencias/comparativa/*.png` (gráficas matplotlib).
- Bitácora completa: `docs/bitacora.md`. Hallazgo de las VMs: `evidencias/vm_azure_policy_hallazgo.md`.

## 6. Sala de control en vivo (dónde se tomó la evidencia)

Para que la comparación sea **demostrable en el momento** (y no solo con logs ya cerrados)
se desplegó en la VM un dashboard propio: **https://iotcentraljose.duckdns.org** (nginx con
certificado de Let's Encrypt delante de gunicorn, servido como servicio systemd).

- Muestra los **3 protocolos publicando en vivo** sobre los mismos 3 devices: contador de
  mensajes, latencia última/promedio/mín/máx, payload JSON actual, sparkline y la **salida
  cruda de cada script** (`[MQTT] #… puback … ms`, `[AMQP] … SendComplete`, `[COAP] … 2.04 Changed`).
- Permite **iniciar/detener cada protocolo** desde el navegador (y una corrida cronometrada
  de 90 s con los tres a la vez).
- Tiene un apartado de **evidencia**: congela la corrida en curso y genera
  `evidencias/capturas/captura-<fecha>/` con los `*.jsonl`, los stdout, `resumen.json`,
  `reporte.md` (tabla lista para pegar) y 4 gráficas PNG; además expone una página
  imprimible en `/informe` y un `.zip` con todo.
- Incluye el **diagrama de la arquitectura real** (los 3 clientes, el gateway CoAP, los
  puertos y la dirección del flujo) y la tabla comparativa teórico-vs-observado en vivo.
- Tiene una sección **«🔬 Cómo viaja el mensaje»** para explicar los protocolos visualmente:
  - **carrera de latencia**: un punto por mensaje real recorriendo la pista VM → IoT Central,
    un carril por protocolo, con el valor en ms al llegar;
  - **pila de protocolos** de cada uno (aplicación / sesión-link / transporte / seguridad / red,
    y el puente del gateway en CoAP);
  - **peso real del mensaje**: 60 B de datos frente a la cabecera fija (MQTT 2 B, AMQP 8 B,
    CoAP 4 B), con la aclaración de que el costo de AMQP está en el handshake (TLS+CBS+attach)
    y el de MQTT en el topic y las tramas TCP/TLS;
  - **secuencia del último intercambio** con los tiempos medidos en vivo
    (PUBACK / disposition SendComplete / RTT CoAP + forwarding del gateway);
  - ***qué mide* cada KPI**, *cuándo usar* cada protocolo y un **glosario** de 12 términos.
- Infraestructura: nginx (80/443, redirect 80→443, TLS de Let's Encrypt con renovación
  automática por `certbot.timer`) → gunicorn en `127.0.0.1:8080` bajo el servicio systemd
  `taller4-dashboard`. El puerto 8080 no está expuesto a Internet.
- **Robustez de la demo:** el dashboard incluye un *vigilante* que relanza un cliente si se cae
  o si se pasa de memoria (sin borrar la corrida), rota los logs al pasar 40 MB y el servidor
  quedó con swap de 2 GB, journald limitado a 200 MB y memoria máxima acotada para el servicio;
  probado matando el cliente AMQP y el gateway CoAP (ambos volvieron solos).

Las métricas citadas arriba provienen de estas capturas y de las corridas formales de la VM.
