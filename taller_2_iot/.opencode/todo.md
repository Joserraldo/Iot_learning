# Mission: UNAB-Ambiental — Laboratorio 2

## M1: Verificar entorno + correr script en VM | status: completed
### T1.1: Preparar archivos locales | agent:Worker | status: completed
- [x] S1.1.1: Crear docs/bitacora.md con cabecera cronológica
- [x] S1.1.2: Crear requirements.txt (con flask)
- [x] S1.1.3: Crear .gitignore (incluir .env)

### T1.2: Conectar a VM por SSH e inspeccionar | agent:Worker | status: completed
- [x] S1.2.1: Probar conexión SSH, listar directorio home | verified | evidence: bitacora 20:50 SSH OK, live SSH cmds confirm access
- [x] S1.2.2: Subir python-vm-01.py, .env, requirements.txt si no existen en VM | verified | evidence: bitacora 20:50 files uploaded to ~/taller_iot/
- [x] S1.2.3: Activar/crear venv, pip install, verificar carga de .env | verified | evidence: bitacora 20:50 venv created, deps installed, 5 env vars verified

### T1.3: Primer run de python-vm-01.py | agent:Worker | status: completed
- [x] S1.3.1: Ejecutar script, confirmar "Conectado a IoT Central." + telemetría | verified | evidence: bitacora 20:55 log "Conectado a IoT Central.", DPS assigned, telemetry 10s
- [x] S1.3.2: Registrar en bitácora (sin datos sensibles) | verified | evidence: bitacora 20:55 entry, no secrets

## M2: Mini dashboard local (Flask embebido) | status: completed
### T2.1: Extender python-vm-01.py con Flask | agent:Worker | depends:T1.3 | status: completed
- [x] S2.1.1: Añadir servidor Flask en hilo separado (no bloquea asyncio) | verified | evidence: python-vm-01.py L126-130 threading.Thread(daemon=True) starts Flask before client
- [x] S2.1.2: GET / — HTML con auto-refresh (Temperature/Humidity/Iluminance/semaforo/Set_temp_hvac/últimos comandos) | verified | evidence: python-vm-01.py L110-112 @app.get("/") render HTML_PAGINA con fetch() 3s (L74,L92), tarjetas L63-68, tabla comandos L69-70
- [x] S2.1.3: GET /api/estado — JSON endpoint | verified | evidence: python-vm-01.py L115-123 jsonify telemetria/semaforo/set_temp_hvac/comandos
- [x] S2.1.4: Probar en VM puerto 5000, documentar firewall | verified | evidence: bitacora 21:00 puerto 5000 en 0.0.0.0, ufw inactive, bloqueo externo, túnel SSH documentado

### T2.2: Verificar dashboard | agent:Reviewer | depends:T2.1 | status: completed
- [x] S2.2.1: curl localhost:5000, curl /api/estado | verified | evidence: live curl HTTP 200 (3077 bytes) en / y JSON en /api/estado
- [x] S2.2.2: Registrar evidencia en bitácora | verified | evidence: bitacora 21:00 entry con diagnóstico firewall

## M3: Proyecto Wokwi (ESP32 simulado) | status: completed
### T3.1: Crear carpeta wokwi/ | agent:Worker | status: completed
- [x] S3.1.1: sketch.ino — DPS + MQTT TLS, DHT22, potenciómetro -> Iluminance, command handler setAlertLed | verified | evidence: wokwi/sketch.ino existe (76 líneas) con PIN_DHT=15, PIN_POT=A0, PIN_LED=2, handler setAlertLed (L63-75), DHT.h include; AzureIoT.h/.cpp (SDK oficial) copiados a wokwi/
- [x] S3.1.2: diagram.json — ESP32 + DHT22 + potenciómetro + LED | verified | evidence: wokwi/diagram.json JSON válido (json.load OK), wokwi-esp32-devkit-v1 + dht22 + potentiometer + led rojo, conexiones GND/3V3/D15/A0/D2
- [x] S3.1.3: libraries.txt — librerías necesarias | verified | evidence: wokwi/libraries.txt con "Azure SDK for C@1.1.8" y "DHT sensor library@1.4.6"
- [x] S3.1.4: Documentar en bitácora pines, librerías, problemas de conexión | verified | evidence: bitacora 21:05 entry (pines GPIO15/36/2, librería elegida, nota Wokwi-GUEST + global.azure-devices-provisioning.net:8883)

## M4: Rule + tabla comparativa + capturas | status: completed
### T4.1: Proporcionar texto de Rule | agent:Planner | status: completed
- [x] S4.1.1: Texto exacto: "Temperature > 28 → Estado_semaforo_LED = 'Rojo'" | verified | evidence: bitacora 21:09 entry "Rule por umbral" con nombre Alerta_Temperatura_Alta, condición Temperature > 28, acción Estado_semaforo_LED="Rojo", pasos de portal
- [x] S4.1.2: Registrar en bitácora cuando el usuario confirme | verified | evidence: bitacora 21:18 entry "Confirmación: Rule configurada en el portal"

### T4.2: Tabla comparativa en docs/bitacora.md | agent:Worker | status: completed
- [x] S4.2.1: Columnas: Origen, cómo se genera, latencia, facilidad debug, fallos de red | verified | evidence: bitacora L76-80 tabla con 5 columnas exactas
- [x] S4.2.2: Completar con observaciones reales de cada etapa | verified | evidence: 3 filas (Simulador nativo, Python-VM 23z8rpgm6s4, Wokwi ESP32) con observaciones reales por etapa

### T4.3: Lista de capturas pendientes | agent:Worker | status: completed
- [x] S4.3.1: Enumerar screenshots necesarios en /evidencias | verified | evidence: bitacora 21:09 lista de 8 capturas (01-08) con nombres y descripciones

## M5: Verificación final | status: completed
### T5.1: Full System Verification | agent:Reviewer | depends:M1,M2,M3,M4 | status: completed
- [x] S5.1.1: Revisar bitácora completa y cronológica | verified | evidence: 10 entries (20:48→21:18) en orden cronológico estricto, sin saltos ni superposiciones
- [x] S5.1.2: Verificar que no hay secretos expuestos | verified | evidence: bitácora solo nombres/longitud de vars; python-vm-01.py usa os.environ; sketch.ino placeholders <DPS_ID_SCOPE>; .gitignore cubre .env
- [x] S5.1.3: Confirmar todos los entregables listos | verified | evidence: python-vm-01.py, requirements.txt, .gitignore, docs/bitacora.md, wokwi/{sketch.ino, diagram.json, libraries.txt, iot_configs.h, AzureIoT.h, AzureIoT.cpp} — 11 archivos entregables

## M6: Wokwi local en VS Code (evitar servidores wokwi.com) | status: completed
### T6.1: Toolchain + compilación firmware | agent:Worker | status: completed
- [x] S6.1.1: Instalar arduino-cli (winget ArduinoSA.CLI 1.5.1) | verified | evidence: `arduino-cli version` → 1.5.1; MSI añadió `C:\Program Files\Arduino CLI\` al PATH del sistema
- [x] S6.1.2: Configurar board URL ESP32 + core update-index | verified | evidence: additional_urls=espressif package_esp32_index.json descargado
- [x] S6.1.3: Instalar core esp32:esp32 + libs (Azure SDK for C, DHT) | verified | evidence: esp32:esp32@3.3.11 installed; Azure SDK for C@1.1.8, DHT sensor library@1.4.7 installed
- [x] S6.1.4: Renombrar sketch.ino→wokwi.ino y compilar a firmware.bin | verified | evidence: compile OK "Sketch uses 1060849 bytes (80%)"; build/wokwi.ino.merged.bin (4MB) generado
- [x] S6.1.5: wokwi.toml→merged.bin + .vscode/tasks.json + README | verified | evidence: firmware='build/wokwi.ino.merged.bin'; Ctrl+Shift+B compila; wokwi/README.md con pasos
- [x] S6.1.6: Validar que el firmware es imagen ESP32 arrancable | verified | evidence: merged.bin layout correcto (bootloader@0x1000, partitions magic 0xAA@0x8000, app magic 0xE9@0x10000); wokwi.ino.bin y bootloader magic 0xE9

### T6.2: Preparar handoff de ejecución al usuario | agent:Worker | depends:T6.1 | status: completed
- [x] S6.2.1: Entregar instrucciones de licencia + compile + simulate | verified | evidence: wokwi/README.md (pasos 1-6 + troubleshooting), .vscode/tasks.json (Ctrl+Shift+B), wokwi.toml→merged.bin

## Handoff al usuario (fuera del scope ejecutable del agente — aceptación en GUI/cuenta propia)
- Reiniciar VS Code → abrir carpeta `wokwi/` → `F1` *Wokwi: Request a new License* (gratis, una vez).
- `Ctrl+Shift+B` (compilar) → `F1` *Wokwi: Start Simulator* → ver en Serial `MQTT client connected` + telemetría.
- Confirmar `esp32-wokwi-01` "Conectado" en Azure IoT Central (Temperature/Humidity/Iluminance).
- Opcional: el agente puede verificar headless si el usuario aporta `WOKWI_CLI_TOKEN`.