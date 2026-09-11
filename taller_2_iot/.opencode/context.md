# Project Context

## Environment
- Language: Python 3.13.1 (local), Python 3.12.3 (VM Ubuntu)
- Runtime: asyncio + azure-iot-device + Flask
- VM: 57.156.62.111 (ssh jtellez312), path remoto ~/taller_iot/
- SSH helper: tools/vm_ssh.py (comando), tools/vm_push.py y tools/vm_upload.py (subir) — credenciales via env VM_HOST/VM_USER/VM_PASS, usar MSYS_NO_PATHCONV=1. paramiko 5.0.0 en .venv.
- GUIA DE PROCESO (cada vez que prendemos la VM): docs/guia-vm-azure.md (Start Azure → export VM_* → vm_ssh start.sh → tail run.log → túnel SSH :5000 → Stop).
- Template IoT Central: consola-unab-ambiental. DTDL real: dtmi:unabAmbientalJose:consolaUnabAmbiental_1pu;1
- Rule REAL del usuario (configurada): `Alerta Temperatura alta` → T > 27 → Email a jtellez312@unab.edu.co ("hola, la temperatura del salon esta muy alta...")
- 3 dispositivos de la misma plantilla = diseño del Lab: simuladores nativos + Python-VM (23z8rpgm6s4) + Wokwi ESP32 (esp32-wokwi-01)

## Current Status (2026-09-03 ~13:00) — WOKWI PARA VS CODE LISTO
- Lab 2 CORE COMPLETO (todo.md 41/41). Dashboard rediseñado PROBADO EN VIVO.
- VM: python-vm-01.py corriendo, dashboard público :5000. Tabla comandos invertida (más reciente arriba).
- **Wokwi migrado a VS Code (simulación LOCAL, sin servidores wokwi.com):**
  - arduino-cli 1.5.1 instalado (MSI, en PATH del sistema `C:\Program Files\Arduino CLI\`).
  - Core esp32:esp32@3.3.11 + libs Azure SDK for C@1.1.8 + DHT sensor library@1.4.7 instaladas.
  - `sketch.ino` renombrado a `wokwi.ino` (arduino-cli exige .ino == nombre de carpeta).
  - Compila OK: `build/wokwi.ino.merged.bin` (80% flash, 16% RAM).
  - `wokwi.toml` apunta a `build/wokwi.ino.merged.bin` + elf. `.vscode/tasks.json` (Ctrl+Shift+B). `wokwi/README.md` con pasos.
  - Wokwi VS Code trae IoT Gateway privado → el ESP32 simulado conecta a Azure real.
  - PENDIENTE runtime: usuario activa licencia Wokwi (F1, una vez) + Start Simulator. Sin token no se puede verificar headless.
- wokwi/iot_configs.h RELLENADO con credenciales reales esp32-wokwi-01 + MODEL_ID real. AÑADIDO a .gitignore.
- wokwi/diagram.json CORREGIDO (pines Wokwi correctos: pot 1/2/3, GPIO15/36/2) — antes no salían cables.
- wokwi/wokwi.toml CREADO (para Wokwi for VS Code v3.7.0, ya instalada en la máquina del usuario).
- wokwi/iot_configs.h: PIN_POT ahora 36 (antes A0).
- docs/bitacora.md: ~16 entradas cronológicas completas (hasta 23:55).
- USUARIO va a APAGAR LA VM desde Azure (Stop). Retomar mañana: Start → SSH → bash ~/taller_iot/start.sh → tail run.log.
- La IP se mantiene al apagar (IP pública Azure).

## Current Status (2026-09-10 ~16:00) — BREVO + HVAC SETPOINT VERIFICADO EN VM
- Misión "Brevo emails (asesor + T>27) + Set_temp_hvac afecta temperatura real + deploy VM" **COMPLETA Y VERIFICADA** (todo.md 10/10, evidencia en `.opencode/integration-status.md`, Reviewer ses_9).
- `python-vm-01.py` md5 `81651aa57ee74dfadf5199d9d56982bf` (local == VM), corriendo en VM, 0 traceback.
- `Set_temp_hvac` (writable) ahora converge la temperatura real (factor 0.15/ciclo): probado 21.6→28.1 con setpoint 30 y 28.2→22.2 al bajar.
- Botón "Llamar asesor" fuerza T 28.5–31 y queda >27 varios ciclos (margen para la Rule de Azure); envía correo Brevo inmediato.
- Alerta automática T>27 (borde de subida + cooldown 10 min) integrada vía helper Brevo (stdlib urllib).
- `.env` local y VM con bloque `EMAIL_API_KEY=` (vacío), `EMAIL_REMITENTE=` (vacío), `EMAIL_DESTINATARIO=jtellez312@unab.edu.co`. Sin llave los correos se OMITEN sin romper telemetría.
- Dashboard público `http://57.156.62.111:5000` responde 200 desde red externa (`/api/estado`, `/api/set-temp`, `/api/llamar-asesor`, `/api/force-reading`).
- Setpoint final dejado en valor nominal 22.0 °C tras las pruebas.

## Pendientes de USUARIO (fuera del scope de esta misión — no son TODO del mission control)
- (usuario) Confirmar entrega real del correo: poner `EMAIL_API_KEY` de Brevo en `.env` de la VM y reiniciar `bash ~/taller_iot/start.sh`; revisar bandeja jtellez312@unab.edu.co (la ruta 201/messageId ya está implementada y probada en modo OMITIDO).
- (usuario) Validar en el portal IoT Central la Rule "Alerta Temperatura alta" T>27 con la telemetría real ya enviada (semáforo rojo + email del hub).
- (usuario) Wokwi runtime: activar licencia Wokwi en VS Code (F1) + Ctrl+Shift+B + Start Simulator. Toolchain y firmware ya listos (ses_7). Opcional headless con `WOKWI_CLI_TOKEN`.
- (usuario) Tomar 8 capturas en `/evidencias` (lista exacta en `docs/bitacora.md`).
- (hecho) Actualizar todo.md/status.md/work-log con enfoque Wokwi-VS-Code — completado ses_7/ses_8/ses_9.


## Notes
- Nunca imprimir/commitear secretos. wokwi/iot_configs.h tiene key real → .gitignore
- Si la VM se apagó, verificar que el dashboard arranca al re-ejecutar start.sh (iniciar_dashboard se llama en main())
- El usuario mañana dirá "continúa el lab 2" y yo leo context.md + bitacora para retomar