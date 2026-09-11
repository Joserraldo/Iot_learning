# Bitácora — UNAB-Ambiental, Laboratorio 2

**Estudiante:** José Alejandro Téllez Prada
**Curso:** IoT + Cloud + Sistemas Distribuidos (UNAB)
**Plantilla:** consola-unab-ambiental

---

## [2026-09-02 20:48] Inicio del Laboratorio 2
- Se revisó el directorio de trabajo local.
- Archivo principal: `python-vm-01.py` (equivalente a `main.py` del prompt).
- `.env` presente (no se imprime su contenido), `.venv/` existente con `azure-iot-device` y `dotenv` instalados.
- No existían `requirements.txt`, `docs/` ni `.gitignore` — se crean en esta sesión.
- **Próximo paso:** Conectar por SSH a la VM (57.156.62.111) para verificar y correr el script.

## [2026-09-02 20:50] Verificación de entorno en la VM
- **Qué se hizo:** Conexión SSH a la VM; se subieron `python-vm-01.py`, `.env` y `requirements.txt` a `~/taller_iot/`. Se instaló `python3.12-venv` (faltaba en la imagen Ubuntu) y se creó `venv/` con las dependencias.
- **Por qué:** El nodo Python del Laboratorio 2 debe correr dentro de la VM (uno de los 8 dispositivos de la flota).
- **Resultado:** `python3` 3.12.3 en la VM. Dependencias instaladas (`azure-iot-device`, `python-dotenv`, `flask`). Las 5 variables de `.env` cargan correctamente (verificado por nombre y longitud, sin imprimir valores). No se expusieron secretos.

## [2026-09-02 20:55] Primer run de python-vm-01.py (conexión OK)
- **Qué se hizo:** Se ejecutó el script en background dentro de la VM (`~/taller_iot/start.sh`, con salida hacia `run.log`).
- **Por qué:** Confirmar que el aprovisionamiento DPS, la conexión a IoT Central y el envío periódico de telemetría funcionan desde la VM.
- **Resultado / evidencia (log):**
  - `Aprovisionando dispositivo via DPS...`
  - `Asignado a hub: ...azure-devices.net`
  - `Conectado a IoT Central.`
  - Telemetría enviada cada 10 s con las variables **Temperature**, **Humidity**, **Iluminance** (valores dentro de rango DTDL).
- **Nota técnica:** Se usó `python -u` (sin buffer) porque `print()` bufferizado no escribía el log en tiempo real.

## [2026-09-02 20:56] Dashboard Flask embebido (extensión de python-vm-01.py)
- **Qué se hizo:** Se añadió un servidor Flask embebido en `python-vm-01.py` que corre en un hilo daemon (no bloquea el loop asyncio). Se agregaron dos rutas:
  - `GET /` — página HTML con auto-refresh (vía `fetch()` cada 3 s) que muestra Temperature, Humidity, Iluminance, Set_temp_hvac, el semáforo y los últimos 5 comandos recibidos.
  - `GET /api/estado` — JSON con el mismo estado.
- **Por qué:** Proporciona una vista de depuración local del "gemelo digital" (el gemelo real sigue siendo el de Azure IoT Central).
- **Resultado:** Flask sirve correctamente en `http://localhost:5000`. Endpoints responden HTTP 200.
- **Nota de compatibilidad:** Se añadió `flask` a `requirements.txt`.

## [2026-09-02 21:00] Prueba de acceso al dashboard desde fuera de la VM
- **Qué se hizo:** Se intentó acceder a `http://57.156.62.111:5000/` desde la máquina local.
- **Resultado:** Timeout de conexión (cURL exit code 28, 12 s).
- **Diagnóstico:** Dentro de la VM, `ufw` está inactivo y `iptables` tiene política ACCEPT. El puerto 5000 está escuchando en `0.0.0.0:5000`. El bloqueo es externo: el firewall del proveedor de nube (o grupo de seguridad) no permite tráfico entrante en el puerto 5000.
- **Solución documentada:** Para acceder al dashboard desde fuera, usar túnel SSH:
  ```
  ssh -L 5000:localhost:5000 jtellez312@57.156.62.111
  ```
  Luego abrir `http://localhost:5000` en el navegador local. Alternativamente, cambiar el puerto a 80/443 (requiere sudo) y solicitar apertura en el firewall del proveedor.

## [2026-09-02 21:05] Proyecto Wokwi (ESP32 simulado)
- **Qué se hizo:** Se creó la carpeta `wokwi/` con 4 archivos:
  - `sketch.ino` — guía de modificación del ejemplo oficial `Azure_IoT_Central_ESP32` (librería **Azure SDK for C** v1.1.8) para añadir DHT22, potenciómetro → Iluminance y handler del comando `setAlertLed`.
  - `diagram.json` — circuito Wokwi: ESP32 DevKit v1 + DHT22 (pin 15) + potenciómetro (pin A0/GPIO36) + LED rojo (pin 2).
  - `libraries.txt` — `Azure SDK for C@1.1.8` y `DHT sensor library@1.4.6`.
  - `iot_configs.h` — plantilla con placeholders para Device ID `esp32-wokwi-01` (creado en el portal con su propia Primary Key, sin reutilizar la del nodo Python).
- **Por qué:** Completar la flota de 8 dispositivos: 6 simuladores nativos + 1 nodo Python (VM) + 1 ESP32 (Wokwi).
- **Pines usados:** DHT22 → GPIO15; potenciómetro → GPIO36 (ADC1 CH0); LED → GPIO2.
- **Librería elegida:** "Azure SDK for C" de Microsoft (sucesor del SDK Arduino deprecado) porque maneja DPS + MQTT TLS automáticamente; la antigua `azure-iot-arduino` está deprecada.
- **Nota sobre conexión:** En Wokwi se usa la red `Wokwi-GUEST` (pública, sin contraseña); el gateway MQTT público de Azure (`global.azure-devices-provisioning.net:8883`) es alcanzable desde Wokwi. Pendiente de validar en ejecución real; si Wokwi no resuelve DNS externo, se documentará el fallo.
- **Pendiente manual:** Crear el device `esp32-wokwi-01` en Azure IoT Central (misma plantilla) y pegar sus valores reales en `iot_configs.h`.

## [2026-09-02 21:09] Rule por umbral en Azure IoT Central (texto para configurar manualmente)
- **Texto exacto para la regla:**
  - **Nombre:** `Alerta_Temperatura_Alta`
  - **Condición:** `Temperature > 28` (umbral superior del rango operativo, 16–32 °C)
  - **Acción:** Cambiar la propiedad `Estado_semaforo_LED` a `"Rojo"`
  - **Cómo configurar en el portal:**
    1. Ir a IoT Central -> Rules -> +New
    2. Seleccionar la plantilla `consola-unab-ambiental`
    3. Condición: `Temperature` > `28`
    4. Acción: "Update property" -> `Estado_semaforo_LED` = `"Rojo"`
    5. Guardar y activar
  - **Nota:** Cuando el usuario confirme que la configuró, se anotará en la bitácora.

## [2026-09-02 21:09] Tabla comparativa — 3 orígenes de datos

| Origen | Cómo se genera el dato | Latencia percibida | Facilidad de debug | Fallos de red observados |
|--------|----------------------|--------------------|--------------------|--------------------------|
| **Simulador nativo** (Azure IoT Central) | IoT Central genera datos sintéticos basados en el rango DTDL. No requiere hardware real. | Inmediata (dentro del portal) | Alta: logs integrados en el portal | Ninguno (datos internos de Azure) |
| **Python-VM** (nodo `23z8rpgm6s4`) | Script Python 3.12.3 en VM Ubuntu: caminata aleatoria dentro de rangos DTDL (16–32 °C, 35–70 %RH, 100–800 lux). Envía cada 10 s a IoT Central. | ~1–2 s desde DPS hasta IoT Central | Media: requiere SSH a la VM, ver `run.log` con `-u` para evitar buffer | Ninguno hasta ahora (DPS + MQTT TLS estables). El puerto 5000 del dashboard no es accesible desde fuera por firewall externo |
| **Wokwi (ESP32)** | ESP32 simulado con DHT22 (Temperature, Humidity) y potenciómetro (Iluminance mapeado 100–800 lux). Envía cada 10 s usando `Azure SDK for C`. | Depende de Wokwi (simulación en navegador) | Baja: requiere depuración por serial en Wokwi; SDK tiene callbacks para comandos | Pendiente de probar; posible firewall de Wokwi para outbound MQTT (puerto 8883) |

## [2026-09-02 21:09] Lista de capturas de pantalla pendientes para `/evidencias`

| # | Nombre de archivo | Descripción |
|---|-------------------|-------------|
| 01 | `01-iot-central-dispositivo-vm.png` | Device `23z8rpgm6s4` en IoT Central mostrando telemetría (Temperature, Humidity, Iluminance) |
| 02 | `02-dashboard-flask-localhost.png` | Dashboard Flask en `http://localhost:5000` (con túnel SSH) mostrando las 5 tarjetas |
| 03 | `03-wokwi-diagrama-circuito.png` | Diagrama del circuito en Wokwi (ESP32 + DHT22 + potenciómetro + LED) |
| 04 | `04-rule-umbral-configurada.png` | Regla `Alerta_Temperatura_Alta` configurada en Azure IoT Central |
| 05 | `05-comparativa-telemetria.png` | Vista de los 3 dispositivos (simulador, VM, Wokwi) enviando telemetría simultánea |
| 06 | `06-bitacora-y-archivos.png` | Estructura del proyecto local (tree) mostrando todos los archivos creados |
| 07 | `07-script-vm-conectado.png` | Log de `python-vm-01.py` mostrando "Conectado a IoT Central." y telemetría |
| 08 | `08-dps-provisioning-log.png` | Log del aprovisionamiento DPS (paso a paso)

## [2026-09-02 21:18] Confirmación: Rule configurada en el portal
- **Qué se hizo:** El usuario confirmó que configuró la Rule en Azure IoT Central.
- **Configuración REAL (confirmada por el usuario):**
  - **Nombre:** `Alerta Temperatura alta`
  - **Condición:** `Temperature > 27`
  - **Acción:** Email a `jtellez312@unab.edu.co` con asunto "hola, la temperatura del salon esta muy alta, porfavor ve a revisar que puede estar pasando"
  - **Plantilla:** `consola-unab-ambiental`
- **Nota:** La regla original del prompt era T>28→semáforo rojo, pero el usuario configuró T>27→Email. Se respeta la configuración real del usuario.

## [2026-09-02 22:30] Rediseño del dashboard — "panel del profesor"
- **Qué se hizo:** Se rediseñó la interfaz Flask de `python-vm-01.py` para que sea el panel que el profesor usa en clase:
  - Semáforo grande con animación (pulso) según temperatura.
  - Tarjetas de Temperature / Humidity / Iluminance / Set_temp_hvac.
  - Gráfico de historial (canvas) con las últimas 40 lecturas (sin librerías externas).
  - Panel de control con **3 acciones POST** desde la web:
    - `POST /api/set-temp` → cambia la property writable `Set_temp_hvac` (el dispositivo la aplica y la reporta a IoT Central).
    - `POST /api/force-reading` → fuerza una lectura inmediata.
    - `POST /api/llamar-asesor` → fuerza temperatura >27 °C para **disparar la Rule de email** que el usuario configuró (`Alerta Temperatura alta`: T>27 → correo a jtellez312@unab.edu.co).
  - Tabla de comandos recibidos con hora UTC.
  - Refresh del navegador: `fetch()` cada 5 s (antes meta-refresh 3 s, más pesado).
- **Por qué:** El usuario indicó que esta app es la que el profesor usará para ver lecturas, semáforo, setear temperatura y llamar al asesor (mismo trigger del correo).
- **Resultado / evidencia (probado en vivo en la VM):**
  - `POST /api/set-temp {"valor":24.5}` → log: `[Property writable] Set_temp_hvac actualizado desde web a 24.5`
  - `POST /api/llamar-asesor` → log: `[Asesor] Temperatura forzada por encima de 27°C` y siguiente lectura `Temperature: 28.4` (dispara la Rule de email)
  - `/api/estado` ahora incluye `historial`, `ultima_lectura`, `id_salon`.
- **Nota:** La Rule real del usuario quedó confirmada como `Temperature > 27 → Email` (difiere del texto original del prompt que decía >28 → semáforo rojo; se respeta la configurada por el usuario).

## [2026-09-02 21:20] Proyecto Wokwi (ESP32 simulado) — completado
- Archivos creados en `wokwi/`: `sketch.ino` (main, ~589 líneas), `AzureIoT.h/.cpp` (abstracción oficial del Azure SDK for C v1.1.8), `Azure_IoT_PnP_Template.h/.cpp` (plantilla PnP adaptada), `iot_configs.h` (placeholders, sin secretos), `diagram.json`, `libraries.txt`.
- Pines: DHT22 → GPIO15 (Temperature + Humidity), potenciómetro → A0/GPIO36 (analogRead 0..4095 → Iluminance 0..1000 lux), LED rojo → GPIO2 (comando `setAlertLed`).
- Librerías: `Azure SDK for C@1.1.8` (oficial Microsoft, reemplaza a AzureIoTHub obsoleta) + `DHT sensor library@1.4.6` (Adafruit).
- Conexión: DPS (ID Scope) + symmetric key + MQTT sobre TLS (`mqtts://global.azure-devices-provisioning.net`), telemetría JSON `{"Temperature","Humidity","Iluminance"}` cada 10 s, command handler `setAlertLed` responde 202/404.
- Problema de conexión conocido: Wokwi usa la red `Wokwi-GUEST` sin password; los valores reales de `DPS_ID_SCOPE`/`DEVICE_ID`/`DEVICE_KEY` deben reemplazar los placeholders en `iot_configs.h` (device separado `esp32-wokwi-01` en IoT Central, NO reutilizar el del nodo Python).

## [2026-09-02 21:25] Rule de Azure IoT Central (texto original del prompt)
- El prompt original pedía `"Temperature > 28 → Estado_semaforo_LED = 'Rojo'"`.
- **Nota:** el usuario finalmente configuró en el portal una Rule distinta: `T > 27 → Email` (ver entrada 21:18). La semaforización por umbral la replica localmente el script en `calcular_semaforo()`.

## [2026-09-02 21:25] Tabla comparativa: Python (VM) vs ESP32 (Wokwi)

| Origen | Cómo se genera | Latencia | Facilidad de debug | Fallos de red |
|--------|---------------|----------|--------------------|---------------|
| **Python/VM** | Generado por `python-vm-01.py` (azure-iot-device, asyncio) cada 10 s | Baja | Alta: log file `run.log` + dashboard Flask `localhost:5000`, endpoint `/api/estado` | Auto reconnect logic + timeout HTTP observado (puerto 5000 bloqueado por firewall de nube; workaround con túnel SSH) |
| **ESP32/Wokwi** | Generado por `sketch.ino` (Azure SDK for C v1.1.8) leyendo DHT22 + potenciómetro cada 10 s | Depende de internet de Wokwi | Baja: debug por serial monitor 115200 (LogInfo con timestamp) | `WiFi.reconnect` + máquina de estados `azure_iot_stop/start`, re-provisionamiento DPS al reconectar |

- **Observaciones reales:** en la VM se confirmó "Conectado a IoT Central." con telemetría; en Wokwi la verificación queda pendiente de ejecución por el usuario (S3.1.4 registro de problemas de conexión).

## [2026-09-02 21:25] Capturas pendientes (en `/evidencias`)
- Captura del dashboard de IoT Central mostrando telemetría del device Python (VM).
- Captura del device `esp32-wokwi-01` provisionado en IoT Central.
- Captura de la regla configurada (`Temperature > 27` → Email).
- Captura del dashboard Flask local (panel del profesor).
- Captura del serial monitor de Wokwi mostrando "Conectado a IoT Central.".

## [2026-09-02 23:15] Fix orden tabla comandos en dashboard
- **Qué se hizo:** Se invirtió el orden de la tabla de comandos en el dashboard Flask para que el más reciente aparezca arriba.
- **Cómo:** Se agregó `.slice().reverse()` en el JS antes de renderizar las filas de la tabla.
- **Resultado:** Probado en vivo; la tabla ahora muestra el último comando en la primera fila.

## [2026-09-02 23:20] Wokwi — corrección de diagram.json y pines
- **Problema:** El usuario abrió el proyecto Wokwi en wokwi.com y no aparecían cables ("no hay cables").
- **Causa:** El `diagram.json` original usaba nombres de pines que Wokwi no reconoce:
  - El potenciómetro (`wokwi-potentiometer`) tiene pines `1`, `2`, `3` (no `VCC`/`SIG`/`GND`).
  - El ESP32 DevKit v1 usa `GPIO15`, `GPIO36`, `GPIO2` (no `D15`, `A0`, `D2`).
- **Solución:** Reescribir `diagram.json` con los nombres de pines correctos.
- **Además:** `iot_configs.h` cambió `PIN_POT A0` → `PIN_POT 36` para coincidir con el diagrama.
- **Archivos modificados:** `wokwi/diagram.json`, `wokwi/iot_configs.h`.

## [2026-09-02 23:35] Wokwi — relleno de credenciales reales y creación del device
- **Qué se hizo:** El usuario creó el device `esp32-wokwi-01` en Azure IoT Central (misma plantilla, como dispositivo real, no simulado).
- **Credenciales pegadas en `iot_configs.h`:** `DPS_ID_SCOPE=0ne0128547D`, `DEVICE_ID=esp32-wokwi-01`, `DEVICE_KEY` (valor real, no se expone en la bitácora).
- **Model ID alineado:** `IOT_CONFIG_MODEL_ID = dtmi:unabAmbientalJose:consolaUnabAmbiental_1pu;1` (coincide con el @id del DTDL del usuario).
- **Seguridad:** `wokwi/iot_configs.h` se añadió a `.gitignore` para evitar commits accidentales de la key.
- **Nota adicional:** El usuario tiene la extensión "Wokwi for VS Code" v3.7.0 instalada, pero no pudo probar la simulación porque wokwi.com respondió "server busy" y `arduino-cli` no está instalado localmente.

## [2026-09-02 23:55] Cambios menores y mejoras finales
- **Wokwi for VS Code:** Se creó `wokwi/wokwi.toml` para que la simulación local funcione con la extensión de VS Code.
- **Tabla comparativa en bitácora:** Se actualizó la tabla de la sección 21:25 con la información real de los 3 orígenes de datos (Simulador nativo, Python-VM, Wokwi-ESP32).
- **Diagrama de conexiones:** Se documentaron los pines correctos en el `diagram.json` (ver conexiones arriba).
## [2026-09-03 13:03] Wokwi — migración a simulación LOCAL en VS Code (arduino-cli)
- **Decisión del usuario:** dejar de depender de wokwi.com (daba "server busy") y usar **Wokwi for VS Code**, que corre la simulación en local e incluye un **IoT Gateway privado** → el ESP32 simulado puede conectar a Azure real.
- **Hallave clave:** la extensión de VS Code **no compila** el `.ino`; solo simula un **firmware.bin** ya compilado. Había que instalar un toolchain.
- **Toolchain instalado (arduino-cli, elegido sobre PlatformIO):**
  - `winget install ArduinoSA.CLI` → arduino-cli 1.5.1 (añadido al PATH del sistema).
  - Board manager URL ESP32 + `core update-index`.
  - `core install esp32:esp32` → **esp32:esp32@3.3.11** (baja ~1 GB de toolchains).
  - `lib install "Azure SDK for C" "DHT sensor library"` → 1.1.8 y 1.4.7 (+ Adafruit Unified Sensor).
- **Fix de compilación:** arduino-cli exige que el `.ino` se llame como la carpeta → se renombró `sketch.ino` → **`wokwi.ino`**.
- **Compilación OK:** `arduino-cli compile --fqbn esp32:esp32:esp32 --build-path build .`
  → "Sketch uses 1060849 bytes (80%), RAM 16%". Genera `build/wokwi.ino.merged.bin` (imagen completa de flash).
- **Config Wokwi:** `wokwi.toml` ahora apunta a `build/wokwi.ino.merged.bin` (+ `.elf`). Se creó `.vscode/tasks.json` (Ctrl+Shift+B compila) y `wokwi/README.md` con los pasos. `wokwi/build/` añadido a `.gitignore`.
- **Pendiente (runtime, GUI):** el usuario debe reiniciar VS Code, abrir la carpeta `wokwi/`, activar la licencia de Wokwi (F1, gratis, una vez), compilar (Ctrl+Shift+B) y `F1 → Wokwi: Start Simulator`. No hay token de licencia guardado aún, por lo que no se pudo verificar en headless desde aquí.

## [2026-09-03 22:15] Wokwi — PRIMERA EJECUCIÓN EXITOSA (conexión real a Azure) ✅
- **Qué se hizo:** El usuario compiló y corrió la simulación local (Wokwi for VS Code). Serial capturado:
  - `WiFi connected, IP address: 10.13.37.2` (red virtual `Wokwi-GUEST`)
  - `Setting time using SNTP` → `Time initialized!`
  - `MQTT client connected` → DPS: PUT `iotdps-register` → GET `operationstatus` → **asignado al hub** `iotc-47a415d3-...azure-devices.net`
  - Segunda conexión MQTT al hub + suscripciones PnP (`$iothub/methods/POST/#`, `$iothub/twin/res/#`, desired properties)
  - Device info reportado (status 204) y **telemetría cada 10 s** a `devices/esp32-wokwi-01/messages/events/`
- **Resultado:** `esp32-wokwi-01` pasa a *Connected* en IoT Central **mientras la simulación está corriendo** (con el simulador apagado aparece como *Disconnected* — es el comportamiento esperado).
- **Problema detectado en el serial:** los comandos de la plantilla (`Encender_hvac`, `force_reading`) respondían `404 Command not recognized` porque el firmware solo implementaba `setAlertLed` (nombre del ejemplo oficial, no de la plantilla del usuario). El LED nunca podía encenderse desde IoT Central.

## [2026-09-03 22:25] Wokwi — adaptación de comandos a la plantilla consola-unab-ambiental
- **Qué se hizo:** Se modificó `wokwi/Azure_IoT_PnP_Template.cpp`:
  - **`Encender_hvac`** (command): alterna el LED rojo GPIO2, reporta la propiedad `Estado_semaforo_LED` (`ON`/`OFF`) y responde **200** con `{"resultado":"HVAC encendido, LED ON","set_temp_hvac":22.0}`.
  - **`force_reading`** (command): fuerza telemetría inmediata (ignora la ventana de 10 s) y responde **200** con la lectura actual `{Temperature, Humidity, Iluminance}`.
  - **`Set_temp_hvac`** (property writable): ahora se acepta, se guarda y se confirma como reported property con su `response status` (antes solo existía `telemetryFrequencySecs`).
  - **Device info** ahora reporta también los campos de la plantilla: `ID_salon="ESP32-WOKWI-01"`, `Estado_semaforo_LED`, `Set_temp_hvac=22.0`, además del componente `deviceInformation`.
  - `setAlertLed` se conserva por compatibilidad con el ejemplo oficial.
- **Por qué:** Alinear el firmware con el DTDL real de la plantilla (`consola-unab-ambiental`), cuyos comandos son `Encender_hvac` y `force_reading`, para que los botones *Run* de IoT Central tengan efecto físico en la simulación (LED).
- **Compilación:** `arduino-cli compile --fqbn esp32:esp32:esp32 --build-path build .` → OK, 1 080 553 bytes (82% flash), RAM 16%.
- **Nota técnica:** `azure_iot_send_properties_update` y `azure_iot_send_command_response` publican de forma síncrona por MQTT, por lo que es seguro llamarlos dentro del handler del comando (el payload usa el buffer del template, separado del `data_buffer` del cliente AzureIoT).
- **Pendiente del usuario:** reiniciar el simulador con el firmware nuevo y ejecutar `Encender_hvac` desde IoT Central → verificar LED ON en Wokwi + `Estado_semaforo_LED=ON` en el panel del device.

## [2026-09-03 22:25] Lista FINAL de capturas para `/evidencias`

| # | Archivo | Qué debe mostrar | ¿Depende de? |
|---|---------|------------------|--------------|
| 01 | `01-iot-central-dispositivo-vm.png` | Device `23z8rpgm6s4` (VM) en IoT Central con telemetría | VM corriendo |
| 02 | `02-dashboard-flask-localhost.png` | Dashboard Flask (panel del profesor) con semáforo, tarjetas y gráfico | Túnel SSH + VM |
| 03 | `03-wokwi-diagrama-circuito.png` | Circuito Wokwi completo: ESP32 + DHT22 + potenciómetro + LED con cables | Simulación abierta |
| 04 | `04-rule-umbral-configurada.png` | Rule `Alerta Temperatura alta` (T>27 → Email) en IoT Central → Rules | Portal |
| 05 | `05-comparativa-telemetria.png` | Los 3 dispositivos (simulador nativo, VM, Wokwi) con telemetría simultánea | VM + Wokwi encendidos |
| 06 | `06-bitacora-y-archivos.png` | Estructura del proyecto local (tree de la carpeta) | Local |
| 07 | `07-script-vm-conectado.png` | `run.log` de la VM: "Conectado a IoT Central." + telemetría | VM |
| 08 | `08-dps-provisioning-log.png` | Serial de Wokwi: bloque DPS (`iotdps-register` → operación → hub asignado) | Simulación corriendo |
| 09 | `09-wokwi-serial-mqtt-conectado.png` | Serial de Wokwi: `MQTT client connected` + `publishing to devices/esp32-wokwi-01/...` cada 10 s | Simulación corriendo |
| 10 | `10-wokwi-iot-central-conectado.png` | Device `esp32-wokwi-01` en IoT Central: estado *Connected* + telemetría Temperature/Humidity/Iluminance | Simulación corriendo |
| 11 | `11-wokwi-led-comando-encender.png` | **La clave:** LED rojo encendido en Wokwi + resultado `200` del comando `Encender_hvac` en IoT Central (misma pantalla o dos capturas) | Firmware nuevo + comando |
| 12 | `12-wokwi-force-reading.png` | Resultado de `force_reading` con payload `{Temperature, Humidity, Iluminance}` en la pestaña Command | Firmware nuevo |
| 13 | `13-wokwi-sensores-moviendo.png` | DHT22 con sliders movidos + potenciómetro girado, y el valor reflejado en IoT Central | Simulación corriendo |
| 14 | `14-wokwi-set-temp-hvac.png` | `Set_temp_hvac` cambiada desde *Properties* (writable) y confirmada por el device (reported) | Firmware nuevo |

## [2026-09-03 22:40] Entradas complementarias (elementos creados en sesiones previas no anotados)
- **`tools/` — helpers SSH de la VM** (Python + `paramiko`, credenciales por variables de entorno `VM_HOST`/`VM_USER`/`VM_PASS`, nunca en el repo):
  - `vm_ssh.py "<cmd>"` → ejecuta un comando bash en la VM.
  - `vm_push.py <local> <remoto>` → sube un archivo por base64 (robusto con rutas con espacios).
  - `vm_upload.py <local> <remoto>` → sube un archivo por SFTP.
  - `vm_tunnel.py` → abre túnel SSH `-L 5000:localhost:5000` para ver el dashboard Flask desde la máquina local (el puerto 5000 está bloqueado por el firewall de la nube).
- **`docs/guia-vm-azure.md`**: runbook paso a paso para encender y operar la VM (portal → SSH → subir código → `start.sh` → túnel del dashboard). Referencia de los helpers de `tools/`.
- **Fix de watchdog en `wokwi.ino` (`setup()`):** en Wokwi el handshake TLS es muy lento por el tope de CPU del simulador y el IDLE task no resetea el *Task Watchdog* a tiempo → reboot a mitad de la conexión. Solución: `esp_task_wdt_delete(NULL)` + reconfigurar a 60 s con `trigger_panic=false`. Sin esto, la simulación reiniciaba antes de completar DPS.
- **Error benigno conocido en el serial (no requiere fix):** `No PUBLISH notification expected` al conectar al hub — ocurre cuando IoT Central tenía un comando encolado (`force_reading`) que llega mientras la máquina de estados del ejemplo aún está procesando el SUBACK. El comando encolado se pierde, pero los comandos posteriores se reciben y responden correctamente (verificado: `Encender_hvac`/`force_reading` entregados y respondidos).
- **Orden de la bitácora:** las entradas del 02-09 no están estrictamente cronológicas (21:20 aparece tras 21:25, etc.); se deja así por ser registro histórico, no se reescriben.

## [2026-09-10 12:00] Dashboard publicado en internet + diagnóstico del navegador
- **Qué se confirmó:** el dashboard Flask es ahora **accesible desde internet** en `http://57.156.62.111:5000` (el grupo de seguridad de la VM ya permite el puerto 5000; ya no hace falta túnel SSH). Verificado desde red externa: `GET /api/estado` → HTTP 200 con datos en vivo.
- **Problema reportado por el usuario:** "no abre en el navegador". **Causa:** Chrome fuerza `https://` al escribir solo la IP, y Flask solo habla HTTP → error de conexión. Los logs de `run.log` lo prueban (handshakes TLS rechazados con 400).
- **Solución:** escribir el protocolo completo `http://57.156.62.111:5000` (o usar Firefox). No es un bug del servidor.

## [2026-09-10 12:30] Set_temp_hvac (writable) ahora AFECTA la temperatura real del nodo
- **Qué se hizo:** `generar_lectura()` cambió de caminata aleatoria pura a un **modelo de primer orden**: la temperatura converge hacia el setpoint en cada ciclo de 10 s:
  ```python
  t = estado["temperature"] + (setpoint - estado["temperature"]) * 0.15 + random.uniform(-0.4, 0.4)
  estado["temperature"] = round(min(32, max(16, t)), 1)
  ```
- **Por qué:** el taller exigía que la property writable tuviera un efecto físico real en el gemelo, no solo guardarse. Ahora cambiar `Set_temp_hvac` (desde IoT Central o desde el dashboard) **mueve la temperatura del salón** en vivo (~2 min de convergencia).
- **El factor 0.15 es intencional:** al forzar T≈29–31 °C con el botón de asesor, la temperatura se mantiene >27 durante varios ciclos (la Rule de Azure dispara con holgura) y aun así se ve la curva bajar hacia el setpoint.
- **Evidencia en vivo:** setpoint 30 → T subió 21.6→22.6→23.8→…→28.1 (monótono); setpoint 16 → T bajó 28.2→…→22.2. Probado bidireccional.
- **Fix asociado (hallazgo de revisión):** el endpoint `POST /api/set-temp` acotaba 10–35 °C, fuera del rango DTDL (16–32). Se alineó el clamp a **16..32** en backend (`valor = round(min(32, max(16, valor)), 1)`) y en el input HTML (`min="16" max="32"`). Probado: `POST {"valor":5}` → responde `Set_temp_hvac = 16°C`.

## [2026-09-10 13:00] Correo de alertas PROPIO vía Brevo (API transaccional)
- **Contexto:** la Rule de IoT Central solo entrega correos a **usuarios de la app** (rol Viewer) — el correo del profesor nunca llegaba por eso. Solución elegida: servicio externo **Brevo** (plan free, 300 correos/día) llamado directamente desde el nodo Python.
- **Implementación (todo en `python-vm-01.py`, solo stdlib — sin dependencias nuevas):**
  - `enviar_email_brevo(asunto, html)`: `POST https://api.brevo.com/v3/smtp/email` con header `api-key`, vía `urllib.request`. Sincronica y **a prueba de fallos**: nunca lanza excepción (no tumba la telemetría); retorna True solo con HTTP 201 (registra `messageId`); captura `HTTPError` con el detalle JSON de Brevo (401 llave inválida, 400 remitente no verificado, 429 cuota).
  - Se llama con `asyncio.to_thread()` para no bloquear el loop de telemetría.
  - `construir_html_estado()`: cuerpo HTML común — tabla con Temperature, Humidity, Iluminance, Set_temp_hvac, semáforo, ID_salon y hora UTC.
- **Dos disparadores de correo:**
  1. **Botón "Llamar asesor"** → correo **inmediato** `[LLAMADO] Asesor solicitado - Salon A-301` + fuerza T>27 (doble canal: Brevo propio + Rule de Azure). Marca el estado "caliente" para que el trigger automático no duplique el aviso.
  2. **Alerta automática T>27** → correo `[ALERTA] Salon A-301: temperatura alta` solo en **borde de subida** (cruza de ≤27 a >27) con **cooldown de 10 min** — evita spam si la temperatura oscila alrededor del umbral (sin estas guardas, el nodo enviaría un correo cada 10 s).
- **Configuración (`.env`, cero secretos en el código):**
  ```
  EMAIL_API_KEY=xkeysib-...        # Brevo → Settings → SMTP & API
  EMAIL_REMITENTE=jtellez312@unab.edu.co
  EMAIL_DESTINATARIO=jtellez312@unab.edu.co
  ```
  En la VM el `.env` quedó con `chmod 600`. Sin `EMAIL_API_KEY`, todo funciona igual y los correos se registran como `OMITIDO` en `run.log` (probado).
- **Evidencia de envío REAL (16:45:53 UTC):**
  ```
  [Asesor] Temperatura forzada por encima de 27°C para disparar Rule de email
  [Email Brevo] 201 OK messageId=<202609101645.24446317629@smtp-relay.mailin.fr> asunto='[LLAMADO] Asesor solicitado - Salon A-301'
  Enviado: {'Temperature': 28.2, ...}   ← T>27 publicada → también dispara la Rule de Azure
  ```
  El usuario confirmó recepción del correo. ✅
- **Nota de deliverability:** la cuenta Brevo aún no tiene el remitente verificado (`/v3/account` → `senders: []`); el correo puede caer en **spam**. Fix: Brevo → *Senders, domains & IPs* → verificar el correo/dominio UNAB.
- **Nota de seguridad:** la API key quedó escrita en el chat de trabajo; si el repo o las capturas se comparten, **rotarla** en Brevo. La llave solo vive en `~/taller_iot/.env` y en el `.env` local (ambos gitignore); nunca en `python-vm-01.py`.

## [2026-09-10 13:10] Runbook: desplegar y probar los correos desde Windows
```powershell
cd taller_2_iot
# 1. Editar python-vm-01.py y compilar antes de subir
python -m py_compile python-vm-01.py
# 2. Credenciales SSH solo por variables de entorno (no se guardan en el repo)
$env:VM_HOST='57.156.62.111'; $env:VM_USER='jtellez312'; $env:VM_PASS='<passwd>'
# 3. Subar y reiniciar (start.sh hace pkill + setsid nohup > run.log)
python tools\vm_push.py python-vm-01.py /home/jtellez312/taller_iot/python-vm-01.py
python tools\vm_ssh.py "bash ~/taller_iot/start.sh; sleep 25; tail -8 ~/taller_iot/run.log"
# 4. Prueba funcional del botón de asesor
Invoke-RestMethod -Uri 'http://57.156.62.111:5000/api/llamar-asesor' -Method Post
python tools\vm_ssh.py "grep 'Email Brevo' ~/taller_iot/run.log | tail -3"
```
- **Verificaciones automáticas usadas en esta sesión:** sync md5 local==VM, `grep -c Traceback run.log` = 0, `GET /api/estado` externo, convergencia T→setpoint observada en el historial, y 201+messageId de Brevo en el log.
