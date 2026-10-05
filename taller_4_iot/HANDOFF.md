# HANDOFF — Taller 4 (estado tras sesión 2)

**Última actualización:** 2026-10-05 (sesión 3 — sala de control en vivo)
**Lee primero:** `docs/bitacora.md` (todo el contexto y hallazgos).

---

## Estado en una frase

Los **tres protocolos (MQTT, AMQP, CoAP) ya publican a IoT Central desde la VM**, hay
evidencias formales de 90 s, gráficas e informe, y además está desplegada una
**sala de control en vivo** (dashboard Flask) en la VM que permite ver los 3 protocolos,
iniciar/detener cada uno y **capturar la evidencia del informe con un botón**.
**Solo falta: capturas de IoT Central (usuario) y revisión final.**

## Dónde está todo

| Cosa | Dónde |
|---|---|
| Contexto + hallazgos completos | `docs/bitacora.md` |
| Hallazgo VMs perdidas / Azure Policy | `evidencias/vm_azure_policy_hallazgo.md` |
| Código (3 protocolos + gateway + provisioning + gráficas) | `python/` |
| Evidencias locales (jsonl) | `evidencias/{mqtt,amqp,coap}/` |
| Gráficas | `evidencias/comparativa/*.png` |
| Informe | `informe-lab4.md` |
| Herramientas VM | `tools/vm_push.py` (subir), `tools/vm_pull.py` (bajar), `tools/vmexec.py` (ejecutar), `tools/dash_deploy.py` (desplegar el dashboard) |
| **Dashboard en vivo** | **https://iotcentraljose.duckdns.org** (nginx + Let's Encrypt → gunicorn; clave de control `DASH_KEY` del `.env`) |
| Credenciales (NO versionado) | `.env` |
| VM | `52.237.172.24`, user `azureuser`, pass en `.env` (`VM_PASS`) |

## Lo que YA funciona (no rehacer)

- **3 devices dedicados:** `mqtt-baseline-01`, `amqp-lab4-01`, `coap-gateway-01` +
  plantilla `consola-unab-ambiental`.
- **MQTT VM formal:** 9 msgs, puback **avg 114.9 ms** (min 104.0, max 124.3).
- **AMQP VM formal:** 9 msgs `SendComplete`, **avg 148.9 ms** (1er msg 430.1 ms =
  handshake; steady ~114.5 ms).
- **CoAP VM formal:** gateway en background (`setsid`) estable + cliente; 8 msgs
  **RTT avg 120.9 ms**, 8/8 `2.04 Changed`; forwarding gateway avg 119.0 ms.
- **Bug del gateway resuelto:** el `ConnectionDroppedError` en bucle era porque el
  proceso en `nohup ... &` moría al cerrarse la sesión SSH (SIGHUP). Con
  `setsid nohup ... < /dev/null > log 2>&1 &` sobrevive el cierre de SSH y es estable.

## Pendiente (usuario)

1. **Capturas en IoT Central** → `https://clima-salones-app-jose.azureiotcentral.com` →
   Devices: `mqtt-baseline-01`, `amqp-lab4-01`, `coap-gateway-01` → telemetría
   `Temperature`, `Humidity`, `Iluminance` en **Data explorer**. Una captura por
   protocolo con la telemetría fluyendo.
2. Revisar `informe-lab4.md` y las gráficas de `evidencias/comparativa/`.

## Sala de control en vivo (sesión 3) — cómo se usa y cómo se rehace

**URL:** https://iotcentraljose.duckdns.org · **clave de control:** `DASH_KEY` (`.env`)

Infraestructura: **nginx** (80/443, TLS de Let's Encrypt, redirect 80→443) → **gunicorn**
(`127.0.0.1:8080`, servicio systemd `taller4-dashboard`). El :8080 ya no está expuesto.
Comandos útiles en la VM: `sudo systemctl status|restart taller4-dashboard`,
`journalctl -u taller4-dashboard -n 50`, `sudo nginx -t && sudo systemctl reload nginx`,
`sudo certbot certificates`.

| Acción | Cómo |
|---|---|
| Ver los 3 protocolos en vivo | abrir la URL (auto-refresco cada 2.5 s) |
| Iniciar/detener un protocolo (o los 3) | botones de cada tarjeta / barra superior (pide la clave una vez) |
| Corrida cronometrada para el informe | botón **⏱ Corrida cronometrada 90 s + captura** → al terminar captura sola |
| Capturar evidencia del informe | botón **📸 Capturar evidencia** (o `POST /api/evidencia` con `X-Dash-Key`) |
| Página imprimible de evidencia | https://iotcentraljose.duckdns.org/informe (botón Imprimir/PDF) |
| Descargar todo (zip) | https://iotcentraljose.duckdns.org/api/paquete.zip |
| Ver cómo viaja el mensaje | sección «🔬 Cómo viaja el mensaje»: carrera de latencia + pila de protocolos + secuencia real + glosario |
| Redesplegar el dashboard | `python tools/dash_deploy.py` (sube, instala y reinicia el servicio systemd) |
| Rehacer nginx + HTTPS | `python tools/vm_https.py` (una sola vez; no hace falta repetirlo) |

La captura deja en `evidencias/capturas/captura-<fecha-hora>/`: los `*.jsonl` de los 3
protocolos + su stdout (`mqtt-stdout.log`, …), `resumen.json`, `reporte.md` (tablas listas
para pegar) y 4 PNG (`barras_latencia`, `serie_temporal`, `boxplot_latencias`,
`bytes_por_mensaje`).

> Ojo: `.gitignore` ignora `*.jsonl` — si quieres versionar las capturas usa `git add -f`.

### Robustez y mantenimiento (para que aguante hasta diciembre)

- **Vigilante propio:** si un cliente se cae o se pasa de memoria (>260 MB), el dashboard lo
  relanza solo **sin borrar el log** (la corrida sigue) y lo anota en
  `evidencias/autoreinicio.log`. El nº de reinicios se ve en la tarjeta del protocolo.
- **Rotación:** cualquier `live*.jsonl` de más de 40 MB se vacía automáticamente (los scripts
  escriben con `O_APPEND`, así que siguen escribiendo al final).
- **Servidor endurecido** con `python tools/vm_robustez.py`: swap de 2 GB en `/etc/fstab`
  (la VM tiene 896 MB y no tenía swap), journald limitado a 200 MB, `vm.swappiness=10`, y
  `MemoryMax=450M` en el servicio.
- **Consumo medido:** dashboard ≈ 111 MB; clientes 20–42 MB cada uno; disco +~25 MB/día;
  23 GB libres. CPU ~5 % de 2 vCPU.
- **Reinicio de la VM:** probado — vuelve en ~20 s y todo arranca solo (nginx, dashboard y, vía
  vigilante, los 3 protocolos con los contadores continuando). `KillMode=process` hace que
  actualizar el dashboard **no** corte la corrida en curso.
- **Si algo no responde:**
  `sudo systemctl status taller4-dashboard` · `journalctl -u taller4-dashboard -n 50` ·
  `tail -20 ~/taller_4_iot/evidencias/autoreinicio.log` · `sudo nginx -t`
- **Renovación del certificado:** automática (`certbot.timer`); para probarla sin riesgo:
  `python tools/vm_https.py --dry-run`.
- **Riesgos externos:** (1) si la VM se **desasigna** la IP pública puede cambiar y DuckDNS
  quedaría mal — no desasignarla; (2) **DuckDNS borra subdominios** tras ~30 días sin
  actualización → conviene un cron diario con el token; (3) que no se agote el crédito de Azure.

## Cómo reproducir las corridas en la VM

```bash
cd ~/taller_4_iot
# MQTT
.venv/bin/python -u python/mqtt_baseline.py --duration 90 --interval 10 --log evidencias/mqtt/vm-formal.jsonl
# AMQP
.venv/bin/python -u python/amqp_sdk.py --duration 90 --interval 10 --log evidencias/amqp/vm-formal.jsonl
# CoAP: gateway DETACHED (sobrevive el cierre de SSH) + cliente
setsid nohup .venv/bin/python -u python/coap_gateway.py --log evidencias/coap/vm-gw-formal.jsonl > evidencias/coap/vm-gw-formal.log 2>&1 < /dev/null &
sleep 15
.venv/bin/python -u python/coap_client.py --duration 75 --interval 10 --log evidencias/coap/vm-client-formal.jsonl
```

## Notas de seguridad

- `.env` y `.dps_cache.json` están en `.gitignore` — **nunca** commitear.
- `VM_PASS` vive solo en `.env`.
- Si se pegan logs en el informe, verificar que no contengan SAS/keys.
