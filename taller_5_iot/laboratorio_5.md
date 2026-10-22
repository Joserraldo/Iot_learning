# Universidad Autónoma de Bucaramanga
## IoT + Cloud + Sistemas Distribuidos
### LABORATORIO 5: Visualización + reglas / alertas (AMQP, MQTT y CoAP con Grafana en una VM)

> **Nota General:** Inicio de Plataforma propia. Dos sesiones de laboratorio y se entrega un solo informe, al cierre de la segunda sesión. Toma de muestra 4 días con Grafana.

---

## 1. Objetivos
* **Instalar en una máquina virtual** el stack de la plataforma propia.
* **Usar cualquiera de los tres protocolos** como los exige el laboratorio: **MQTT**, **AMQP** y **CoAP**.
* **Ver los datos en Grafana**, instalado y consultado aparte.
* **Definir al menos una regla / alerta por umbral**, dispararla y dejar evidencia.
* **Dejar por 4 días** de toma de datos.

---

## 2. Rol de cada pieza

| Pieza | Rol en este laboratorio | Qué debe quedar andando |
| :--- | :--- | :--- |
| **MQTT, AMQP o CoAP** | El grupo elige cuál de los tres usa para publicar las 3 variables (`temperature`, `humidity`, `illuminance`). Puede usar más de uno. | El protocolo elegido deja mensajes en la VM y queda declarado en el informe. |
| **TSDB** | Historial de la toma de 4 días. | InfluxDB, TimescaleDB o QuestDB. Consulta de los puntos guardados. |
| **Grafana** | Visualización y alertas, instalado y consultado aparte del protocolo. | Grafana OSS en la VM, datasource a la TSDB, dashboard con la ventana de 4 días y al menos una alerta. |

> **Nota de arquitectura:** Grafana no es el protocolo de ingesta: solo lee la TSDB. La toma de 4 días tiene que verse en el dashboard, no solo en un log suelto. **Docker Compose es el camino preferido.**

---

## 3. Sesión 1 - Stack en la VM e inicio de la toma
VM con Docker. Levantar el protocolo elegido (MQTT, AMQP o CoAP), la TSDB y dejar Grafana instalado.

* **Publicador** con las 3 variables del escenario, por el protocolo elegido.
* **Escritura en la TSDB**, con marca de tiempo real.
* **Arrancar la toma de 4 días** antes de cerrar la sesión, de modo que Grafana pueda mostrar esa ventana al entregar.

> **Cierre de sesión 1 (sin entrega):** el protocolo elegido escribe en la TSDB y la toma de 4 días ya está corriendo.

---

## 4. Sesión 2 - Grafana, alerta y lectura de la muestra
Grafana se abre aparte, con datasource a la TSDB. El dashboard muestra la toma, no una demo de unos minutos.

* **Serie temporal** de cada variable sobre la ventana de 4 días.
* **Al menos un stat o gauge** con unidad y rango del escenario.
* **Título y una línea** de qué mira el operador.
* **Una alerta de umbral:** condición, ventana y acción (email, webhook, log o canal de prueba). Forzar el valor desde el publicador y capturar el disparo.
* Si la toma aún no completa los 4 días al cierre de la sesión, el informe indica la fecha de corte y la evidencia se adjunta al entregar.

> **Cierre de sesión 2:** un compañero de otro grupo lee el dashboard sin explicación, y la alerta quedó evidenciada.

---

## 5. Entrega
Un solo informe, al cierre de la segunda sesión. No hay entrega parcial al final de la primera. La muestra de 4 días en Grafana forma parte de ese informe.

* **Informe (1-2 páginas):**
  * Diagrama: Protocolo elegido $\rightarrow$ TSDB $\rightarrow$ Grafana.
  * Justificación del protocolo.
  * Umbral de la alerta.
  * Ventana de 4 días (inicio, fin, huecos).
  * Qué falló al instalar en la VM.
* **Repositorio (Repo):**
  * `docker-compose.yml` o scripts.
  * Código del publicador.
  * `README` de cómo levantar la VM (sin secretos).
  * Carpeta `/evidencias` (consulta, dashboard de 4 días, alerta disparada).

---

## 6. Rúbrica de Evaluación

| Criterio | Peso |
| :--- | :---: |
| Protocolo elegido (MQTT, AMQP o CoAP) publicando las 3 variables | **20%** |
| Grafana aparte, con la toma de 4 días visible | **30%** |
| Alerta de umbral disparada y evidenciada | **25%** |
| Stack reproducible, informe único y README | **25%** |

---

## 7. Recursos Sugeridos
* **MQTT:** Mosquitto o EMQX.
* **AMQP:** RabbitMQ u otro broker (declarar 0-9-1 o 1.0).
* **CoAP:** libcoap, aiocoap o Californium.
* **Bases de datos (TSDB):** InfluxDB, TimescaleDB o QuestDB.
* **Grafana:** Grafana OSS (datasources, rango de 4 días y alerting).
* **Despliegue:** Docker Compose, pensando en la migración posterior a la Raspberry Pi.

---

## 8. Descripción de Imágenes o Recursos Visuales del Documento

* **Página 1:** El documento no contiene diagramas ni fotografías complejas. En la parte superior derecha presenta el logotipo e identificación de la asignatura: *"Universidad Autónoma de Bucaramanga | IoT + Cloud + Sistemas Distribuidos"*.
* **Estructura gráfica general:** Utiliza tablas con bordes oscuros para resumir los roles de las piezas del software y la rúbrica de evaluación del laboratorio.