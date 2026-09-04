# Wokwi for VS Code — UNAB-Ambiental (Laboratorio 2)

Simula el **ESP32** en tu propia máquina con la extensión **Wokwi for VS Code**,
**sin depender de los servidores públicos de wokwi.com** (los que daban "server busy").

La extensión trae un **IoT Gateway privado integrado**, así que el ESP32 simulado
sale a internet real y **conecta de verdad a Azure IoT Central** con el dispositivo
`esp32-wokwi-01`.

---

## Requisitos (ya instalados en esta sesión)

- VS Code + extensión **Wokwi for VS Code** (`wokwi.wokwi-vscode`) ✔
- **arduino-cli** en `C:\Program Files\Arduino CLI\` (en el PATH del sistema) ✔
- Core **esp32:esp32@3.3.11** ✔
- Librerías **Azure SDK for C@1.1.8** y **DHT sensor library@1.4.7** ✔

## Estructura

| Archivo | Qué hace |
|---|---|
| `wokwi.ino` | Sketch principal (antes `sketch.ino`; renombrado porque arduino-cli exige que el `.ino` se llame como la carpeta). |
| `AzureIoT.*`, `Azure_IoT_PnP_Template.*` | SDK Azure + plantilla PnP (telemetría + comando `setAlertLed`). |
| `iot_configs.h` | Credenciales WiFi/Azure y pines. **No comitear** (está en `.gitignore`). |
| `diagram.json` | Circuito: ESP32 + DHT22(GPIO15) + potenciómetro(GPIO36) + LED(GPIO2). |
| `wokwi.toml` | Le dice a Wokwi qué firmware simular (`build/wokwi.ino.merged.bin`). |
| `.vscode/tasks.json` | Tarea "Compilar firmware ESP32" (Ctrl+Shift+B). |
| `build/` | Firmware compilado (generado, en `.gitignore`). |

---

## Cómo ejecutar (una vez)

1. **Reinicia VS Code** para que tome el PATH nuevo de arduino-cli.
2. Abre **esta carpeta `wokwi/`** como workspace (File → Open Folder → `wokwi`).
   - Wokwi busca `wokwi.toml` en la **raíz del workspace**, por eso se abre `wokwi/`, no el proyecto completo.
3. **Activa la licencia (una sola vez):** `F1` → *Wokwi: Request a new License* → se abre el navegador → copia el token y pégalo en VS Code. (Es gratis.)
4. **Compila:** `Ctrl+Shift+B` (o `Terminal → Run Task → Compilar firmware ESP32`).
   - Equivale a: `arduino-cli compile --fqbn esp32:esp32:esp32 --build-path build .`
   - Debe terminar con "Sketch uses ... bytes".
5. **Simula:** `F1` → *Wokwi: Start Simulator*. Se abre la pestaña del circuito.
   - Abre el **Serial** dentro de la simulación: verás `Connecting to WIFI Wokwi-GUEST`, luego `MQTT client connected`, y telemetría cada 10 s.
6. En **Azure IoT Central** (app `consola-unab-ambiental`) el dispositivo `esp32-wokwi-01`
   pasará a *Conectado* y mostrará `Temperature`, `Humidity`, `Iluminance`.

## Cambiar valores y volver a compilar

Edita `iot_configs.h` o `wokwi.ino` → vuelve a `Ctrl+Shift+B` → *Start Simulator*.

## Solución de problemas

- **"firmware not found" / no arranca:** asegúrate de haber compilado (paso 4). Si el
  `merged.bin` no arranca, cambia en `wokwi.toml` `firmware` a `build/wokwi.ino.bin`.
- **No conecta a Azure:** revisa que `esp32-wokwi-01` exista en IoT Central con la misma
  clave de `iot_configs.h`, y que el `MODEL_ID` coincida con la plantilla.
- **WiFi:** Wokwi usa la red virtual `Wokwi-GUEST` (sin password); el gateway integrado la
  saca a internet. No requiere que tu PC esté en esa red.
- **arduino-cli no encontrado en terminal:** reinicia VS Code (el PATH se actualiza al reinstalar).
