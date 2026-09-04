# Mission Status

## Progress
- .opencode/todo.md: 33/33 checkboxes [x] (100% ejecutable por el agente); 0 pendientes; 0 M/T con status no-completed
- Issues: 0 unresolved (sync-issues.md vacío)
- Workers: 0 active
- Verification Strategy: toolchain + compilación reproducible (exit 0) + imagen ESP32 validada (magic bytes/offsets). Runtime = handoff GUI/cuenta del usuario (documentado en wokwi/README.md).
- Execution Status: pass (build verificado 2x, exit 0)

## Current Phase
M6 Wokwi local en VS Code — COMPLETADO (toolchain, compile, config, validación, handoff).

## Handoff (usuario, fuera de scope del agente)
1. Reiniciar VS Code → abrir carpeta `wokwi/`
2. F1 → Wokwi: Request a new License (gratis, una vez)
3. Ctrl+Shift+B (compilar) → F1 → Wokwi: Start Simulator
4. Verificar `esp32-wokwi-01` Conectado en Azure IoT Central
- Opcional: verificación headless por el agente con WOKWI_CLI_TOKEN.
