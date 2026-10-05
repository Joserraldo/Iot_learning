# LABORATORIO 4
## AMQP + tercer protocolo
### Comparación con MQTT hacia IoT Central

**Universidad Autónoma de Bucaramanga | IoT + Cloud + Sistemas Distribuidos | Lab 4 · v3**

---

## 1. Objetivos

- Entender el rol de AMQP en Azure (IoT Hub / IoT Central, Service Bus, Event Hubs) frente a MQTT.
- Publicar las mismas ≥ 3 variables hacia IoT Central usando transporte AMQP desde la VM.
- Investigar e implementar un tercer protocolo justificado (HTTP/HTTPS, MQTT sobre WebSockets, CoAP u otro).
- Construir una tabla comparativa MQTT · AMQP · tercer protocolo y recomendar qué usar en cada capa de la plataforma propia.

## 2. Por qué AMQP ahora

En el Lab 3 el transporte visible fue MQTT. IoT Central / IoT Hub también hablan AMQP y AMQP sobre WebSockets (puerto 5671 / 443). Azure usa AMQP de forma intensiva en el plano de servicio (Service Bus, Event Hubs): sesiones, enlaces, créditos y entrega con garantías más ricas que el pub/sub ligero de MQTT. Hoy no se abandona Central: se cambia el transporte del dispositivo Python y se añade un tercer protocolo para cerrar el mapa.

| Protocolo | Dónde se prueba | Destino mínimo |
|---|---|---|
| MQTT (Lab 3) | VM + Wokwi (ya hecho) | IoT Central. Baseline de la comparación. |
| AMQP | Python en la VM | IoT Central / IoT Hub con transporte AMQP (SDK o cliente AMQP). Las 3 variables deben verse en la misma app. |
| Tercero (elección del grupo) | VM (y Wokwi solo si el protocolo cabe en el ESP virtual) | HTTP(S) o MQTT-WS hacia Central, o CoAP/MQTT-SN hacia un endpoint propio justificado. |

CoAP y MQTT-SN no son nativos de IoT Central. Si los eligen, el cliente mínimo puede apuntar a un endpoint propio o de prueba; hay que decirlo en el informe y no fingir que Central lo recibe directo.

### Requisito adicional del grupo: tres dispositivos/protocolos

Para esta versión del laboratorio, el trabajo debe demostrar y comparar **tres dispositivos o clientes de comunicación**, usando tres protocolos diferentes:

1. **Dispositivo/cliente MQTT** — corresponde al trabajo del Laboratorio 3 y funciona como línea base.
2. **Dispositivo/cliente AMQP** — debe implementarse desde la VM y publicar las mismas 3 variables hacia IoT Central / IoT Hub.
3. **Dispositivo/cliente con un tercer protocolo** — el grupo debe implementar un dispositivo o cliente adicional usando **CoAP, WebSocket/MQTT sobre WebSockets, HTTP/HTTPS u otro protocolo técnicamente justificado**.

La intención es que los tres casos sean demostrables y permitan observar directamente las diferencias entre los protocolos. No se trata solamente de investigar las características de cada protocolo: debe existir evidencia de funcionamiento del tercer cliente.

#### Opción recomendada para el tercer dispositivo

Se puede utilizar **CoAP** como tercer protocolo para representar un dispositivo IoT ligero/constrained, especialmente si el grupo quiere contrastar un protocolo basado en UDP y bajo overhead frente a MQTT y AMQP.

También se puede utilizar **WebSocket** o **MQTT sobre WebSockets** si resulta más conveniente para demostrar comunicación sobre el puerto 443 y escenarios detrás de firewalls.

La elección debe quedar justificada técnicamente y relacionada con un caso de uso de la plataforma.

#### Arquitectura esperada

El laboratorio debe dejar clara una arquitectura similar a:

```text
                    ┌─────────────────────────┐
                    │       IoT Central       │
                    │ / IoT Hub / plataforma  │
                    └────────────┬────────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             │                   │                   │
             │                   │                   │
        MQTT │              AMQP │          Tercer protocolo
             │                   │          (CoAP / WS / HTTP...)
             │                   │                   │
      ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
      │ Dispositivo │     │ Dispositivo │     │ Dispositivo │
      │ MQTT        │     │ AMQP        │     │ Protocolo 3 │
      │ Lab 3       │     │ Lab 4       │     │ nuevo       │
      └─────────────┘     └─────────────┘     └─────────────┘
```

El diagrama final del informe debe ser **ilustrativo y adaptado a la implementación real del grupo**, mostrando como mínimo:

- Los tres dispositivos/clientes.
- El protocolo utilizado por cada uno.
- La VM cuando participe en la comunicación.
- IoT Central / IoT Hub o el endpoint propio utilizado.
- Dirección del flujo de datos.
- Las 3 variables de telemetría cuando correspondan.
- Puertos relevantes (por ejemplo 5671/443 cuando aplique).
- TLS/seguridad cuando corresponda.
- Si el tercer protocolo no llega directamente a IoT Central, mostrar explícitamente el endpoint o componente intermedio que recibe los datos.

No se debe dibujar una conexión directa a IoT Central para CoAP, MQTT-SN u otro protocolo que no tenga soporte nativo si la implementación real utiliza un endpoint intermedio.


## 3. Prerrequisitos

- Laboratorio 3 entregado (MQTT explícito y SDK llegando a la misma aplicación IoT Central).
- VM con Python 3.9+, `azure-iot-device` y capacidad de instalar un cliente AMQP (el propio SDK en modo AMQP, `uamqp` / `proton`, o equivalente vigente).
- Credenciales del dispositivo en variables de entorno. Wokwi del Lab 2–3 disponible como testigo MQTT.

## 4. Procedimiento

### Etapa 1 — AMQP hacia IoT Central

En la VM, configurar el cliente de dispositivo para usar transporte AMQP (o AMQP sobre WebSockets si 5671 está bloqueado).

Publicar las 3 variables de la plantilla. Anotar: puerto, TLS, si el dato aparece en Data explorer y qué cambia respecto al MQTT del Lab 3 (conexión persistente, sesiones, tamaño percibido, debug).

**Checkpoint:** al menos un mensaje AMQP de las 3 variables es visible en IoT Central y el grupo puede explicar qué problema resuelve AMQP mejor que MQTT.

### Etapa 2 — Tercer protocolo

Elegir uno y justificarlo en una línea de negocio (no por moda):

- **HTTP/HTTPS** — telemetría REST hacia IoT Hub / Central. Simple, pesado, fácil de depurar.
- **MQTT sobre WebSockets** — mismo modelo MQTT del Lab 3, puerto 443. Útil detrás de firewalls.
- **CoAP** — UDP, bajo overhead; típico de constrained devices. No nativo de Central.
- **Otro justificado** (MQTT-SN, WebSockets puros, etc.).

Implementar un cliente/dispositivo adicional que utilice el tercer protocolo y que envíe las 3 variables o un subset. El resultado debe ser demostrable mediante logs, capturas y/o datos recibidos en el endpoint correspondiente.

Registrar durante la implementación:

- Cómo se establece la conexión.
- Qué protocolo de transporte utiliza.
- Qué puerto utiliza.
- Si utiliza TCP, UDP o WebSocket.
- Si utiliza TLS/HTTPS/WSS u otro mecanismo de seguridad.
- Cómo se estructura el mensaje.
- Cómo se envían las variables de telemetría.
- Qué componente recibe finalmente los datos.
- Ventajas y desventajas observadas.
- Complejidad real de implementación, no la descrita únicamente en un blog o tutorial.
- Diferencias prácticas frente a MQTT y AMQP.

**Checkpoint:** el tercer protocolo funciona de forma demostrable (log + captura y/o evidencia del endpoint receptor).


### Etapa 3 — Tabla comparativa y recomendaciones

Comparar los tres protocolos a partir de la implementación realizada, no únicamente desde teoría. La comparación debe incluir al menos: overhead, latencia percibida, fiabilidad, soporte en microcontrolador / Wokwi, facilidad de debug, paso de firewalls, seguridad/TLS, modelo de comunicación, complejidad de implementación, consumo de recursos y caso de uso ideal.

La comparación debe diferenciar claramente:

- Qué ocurre en MQTT.
- Qué ocurre en AMQP.
- Qué ocurre en el tercer protocolo.
- Qué diferencias se observaron realmente durante las pruebas.
- Qué diferencias son características teóricas del protocolo y cuáles fueron observadas experimentalmente.

Cerrar con recomendaciones concretas:

- Qué protocolo pondrían en el dispositivo (Wokwi / ESP futuro).
- Qué protocolo pondrían entre servicios Azure o en la plataforma propia (Labs 5–8).
- Qué se quedan solo con dos protocolos para el resto del curso y por qué.

## 5. Bitácora de trabajo y análisis experimental

La bitácora debe documentar el proceso realizado con los **tres protocolos**. No debe limitarse a mostrar el resultado final.

Para cada protocolo registrar como mínimo:

| Elemento | MQTT | AMQP | Tercer protocolo |
|---|---|---|---|
| Dispositivo/cliente utilizado | | | |
| Dónde se ejecuta | | | |
| Endpoint/destino | | | |
| Puerto | | | |
| TCP/UDP/WebSocket | | | |
| TLS/seguridad | | | |
| Variables enviadas | | | |
| Formato/estructura del mensaje | | | |
| Evidencia de funcionamiento | | | |
| Latencia percibida | | | |
| Complejidad de implementación | | | |
| Facilidad de debug | | | |
| Problemas encontrados | | | |
| Solución aplicada | | | |

La bitácora debe incluir capturas de los momentos relevantes de configuración, ejecución, errores encontrados, correcciones y pruebas exitosas.

### Análisis comparativo experimental

Después de implementar los tres protocolos, realizar una comparación basada en las evidencias obtenidas.

Como mínimo se debe analizar:

1. **Funcionamiento:** cómo establece comunicación cada protocolo.
2. **Modelo de comunicación:** cómo se publican, transportan y reciben los datos.
3. **Overhead:** qué tan pesado resulta el intercambio de mensajes.
4. **Latencia percibida:** diferencia observada durante las pruebas.
5. **Fiabilidad:** comportamiento ante pérdida, reconexión o errores.
6. **Recursos:** impacto en CPU, memoria, red o complejidad del dispositivo.
7. **Seguridad:** TLS, WSS u otros mecanismos utilizados.
8. **Firewall/NAT:** facilidad para atravesar redes restringidas.
9. **Microcontroladores:** qué tan apropiado resulta para un ESP u otro dispositivo IoT.
10. **Azure/IoT Central:** qué integración existe y si requiere un componente intermedio.
11. **Debug:** facilidad para identificar y solucionar problemas.
12. **Caso de uso:** dónde tendría sentido utilizar cada protocolo en la plataforma propia.

### Diagrama ilustrativo obligatorio

El informe debe incluir al menos **un diagrama de arquitectura** que represente visualmente los tres dispositivos/clientes y sus respectivos protocolos.

Además del diagrama general, se recomienda incluir un segundo diagrama de flujo que muestre:

```text
Dispositivo
    ↓
Protocolo
    ↓
Transporte / conexión
    ↓
Endpoint / broker / gateway
    ↓
IoT Central / IoT Hub / plataforma propia
    ↓
Visualización o almacenamiento de telemetría
```

Los diagramas deben representar la arquitectura que realmente se implementó y no una arquitectura hipotética.

## 5. Entregables

- Informe 1–2 páginas: rol de AMQP en Azure, evidencia de las 3 variables por AMQP en Central, descripción del tercer protocolo, comparación de los tres protocolos y recomendaciones de capa.
- Bitácora del proceso de implementación de MQTT, AMQP y el tercer protocolo, incluyendo problemas, pruebas, capturas y soluciones.
- Tabla comparativa MQTT · AMQP · tercer protocolo basada tanto en documentación como en las pruebas realizadas.
- Diagrama ilustrativo de la arquitectura con los tres dispositivos/clientes y los tres protocolos.
- Repo: script AMQP en la VM + cliente/dispositivo del tercer protocolo + código MQTT reutilizado o documentado + README (dependencias y cómo reproducir, sin secretos) + `/evidencias` (logs, capturas de Central y/o del endpoint elegido).

## 6. Rúbrica

| Criterio | Peso |
|---|---:|
| AMQP publicando las 3 variables a IoT Central / Hub | 30 % |
| Tercer dispositivo/protocolo implementado y justificado | 25 % |
| Rigor de la tabla comparativa MQTT · AMQP · tercero | 25 % |
| Recomendaciones accionables para la plataforma propia | 10 % |
| Informe, bitácora, README, diagrama y evidencias | 10 % |

## 7. Recursos

- Protocolos de dispositivo de IoT Hub / IoT Central: MQTT, AMQP, HTTP y variantes sobre WebSockets.
- `azure-iot-device`: parámetro de transporte AMQP / `AMQP_WS`.
- AMQP 1.0 (sesiones, links, credit-based flow). Service Bus / Event Hubs como contexto Azure.
- CoAP RFC 7252 o documentación del protocolo elegido.


---

# Contexto para ejecución del laboratorio

Este documento debe utilizarse como especificación de trabajo. Si se entrega a un modelo de IA junto con los talleres anteriores, el modelo debe:

1. Revisar primero el Laboratorio 3 para identificar exactamente cómo se implementó MQTT, qué variables se utilizaron, qué dispositivo/cliente se creó y cómo se conectó a IoT Central.
2. Reutilizar lo que ya funciona en MQTT en lugar de reconstruir innecesariamente el trabajo anterior.
3. Implementar AMQP manteniendo, en lo posible, las mismas 3 variables para que la comparación sea equivalente.
4. Implementar un tercer dispositivo/cliente utilizando CoAP, WebSocket/MQTT sobre WebSockets, HTTP/HTTPS u otro protocolo justificado.
5. Mantener evidencia separada de los tres protocolos.
6. Comparar los tres protocolos con base en teoría y resultados experimentales.
7. Documentar en la bitácora tanto los éxitos como los errores y soluciones.
8. Generar un diagrama ilustrativo de la arquitectura real.
9. No inventar que un protocolo es soportado directamente por IoT Central si la implementación requiere un endpoint, gateway o servicio intermedio.
10. Mantener todos los secretos y credenciales fuera del repositorio y del README.

El objetivo final no es únicamente "hacer funcionar AMQP", sino **demostrar mediante tres implementaciones diferentes cómo cambian la comunicación, arquitectura, transporte, seguridad, complejidad y comportamiento de una solución IoT cuando se utiliza MQTT, AMQP y un tercer protocolo**.
