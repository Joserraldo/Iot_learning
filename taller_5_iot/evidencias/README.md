# Evidencias — Taller 5 (MQTT → InfluxDB → Grafana)

Índice de las evidencias del laboratorio. Las **4 primeras** son las que se
imprimen en el anexo del informe
[`../Informe_Lab5_Jose_Tellez_U00060479.pdf`](../Informe_Lab5_Jose_Tellez_U00060479.pdf)
como **Evid. 1–4**; las demás son los logs crudos que respaldan las mediciones
citadas en el texto.

## Anexo gráfico (Evid. 1–4)

| # | Archivo | Qué demuestra | Se cita en |
|---|---|---|---|
| 1 | [`arquitectura-lab5.png`](arquitectura-lab5.png) | Arquitectura real: MQTT → InfluxDB → Grafana dentro de la VM; solo nginx con TLS escucha en público; alerta hacia Brevo SMTP | Sec. 2 |
| 2 | [`alerta/dashboard-4d-con-datos.png`](alerta/dashboard-4d-con-datos.png) | Dashboard Grafana «Lab 5 — Consola ambiental UNAB (4 días)»: series de temperatura/humedad/iluminancia sobre *Last 4 days*, stats (temperatura actual 28.8 °C, humedad 47.3 %, 3 059 muestras en la ventana) y la alerta > 32 °C rotulada en el título. Los tramos rectos son los huecos de la toma por bloques | Secs. 4 y 5 |
| 3 | [`pagina-didactica-taller5.png`](pagina-didactica-taller5.png) | Página didáctica `/taller5/`: recorrido de cada mensaje (publicador → Mosquitto → ingestor → InfluxDB → Grafana), 5 210 mensajes publicados, PUBACK 0.4 ms, hop broker→ingestor 0.4 ms, respuestas HTTP 204 de Influx y últimos mensajes crudos de 90 B | Secs. 3 y 5 |
| 4 | [`toma-bloques-huecos.png`](toma-bloques-huecos.png) | Toma por bloques: 4 bloques de captura (173 · 1 033 · 1 302 · 1 677 muestras) y 3 huecos entre el 17 y el 22 de octubre de 2026 | Sec. 5 |

> Las imágenes son las **mismas** que van incrustadas en el PDF del informe
> (resolución 1879×936 / 1528×579 / 1874×932 / 1528×437), extraídas sin
> recompresión para que el anexo se pueda revisar también en el repo.

## Logs crudos (respaldo de las mediciones)

| Archivo | Contenido |
|---|---|
| [`forzamiento3.jsonl`](forzamiento3.jsonl) | **Disparo forzado de la alerta** (17-oct 05:29–05:59 UTC): 60 mensajes con `Temperature` 34.9–35.1 °C (`--caliente`), topic `lab5/telemetria`, 90 B, con `puback_ms` medido. Es la evidencia de la Evid. de la Sec. 4 |
| [`live-publisher.jsonl`](live-publisher.jsonl) | Corrida del publicador (07-oct 23:21 UTC en adelante): una línea por publicación MQTT QoS 1 con `puback_ms` (0.4–1.7 ms dentro de la VM) |
| [`live-ingest.jsonl`](live-ingest.jsonl) | Corrida del ingestor: una línea por mensaje recibido con `hop_ms` (broker → ingestor) y `influx_status` 204 (escritura aceptada por la TSDB) |
| [`forzamiento.jsonl`](forzamiento.jsonl) / [`forzamiento2.jsonl`](forzamiento2.jsonl) | Corridas de forzamiento anteriores (VM original y primer reintento) — conservan el T=33–38 °C y el orden de los intentos |
| [`alerta/grafana-alerta-vm2.log`](alerta/grafana-alerta-vm2.log) | Log del *sender* de alertas de Grafana: `rule_uid=lab5-temp-32` en estado *Firing*, `Sending alerts to local notifier` **sin errores de autenticación** (17-oct 05:40–05:59 UTC) |
| [`alerta/grafana-alerta-final.log`](alerta/grafana-alerta-final.log) | Fragmento del primer disparo de la alerta (VM original), cuando todavía fallaba el login SMTP |

## Notas

- Los `.jsonl` y `.log` están **forzados** en git (`git add -f`): el
  `.gitignore` del taller excluye ese patrón por costumbre, pero la evidencia
  cruda es parte de la entrega y no se regenera sola.
- Ninguna línea de estos logs contiene secretos: solo métricas, topics y
  variables del escenario.
- Para volver a capturar el dashboard: abrir
  `https://iotcentraljose.duckdns.org/taller5/grafana/d/lab5` y capturar el
  panel «Lab 5 — Consola ambiental UNAB (4 días)».
