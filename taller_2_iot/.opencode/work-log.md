# Work Log

## Active Sessions
- [x] ses_1 (Worker): `python-vm-01.py` (nodo VM + Flask dashboard) - done
- [x] ses_2 (Worker): `requirements.txt` + `.gitignore` - done
- [x] ses_3 (Worker): `docs/bitacora.md` - done
- [x] ses_4 (Worker): `wokwi/` (sketch.ino, diagram.json, libraries.txt, iot_configs.h) - done
- [x] ses_5 (Worker): VM setup + run + dashboard verify - done
- [x] ses_6 (Reviewer): Full System Verification - done (todos los M1-M5 completos, S4.1.2 confirmado por usuario)
- [x] ses_7 (Worker): Wokwi→VS Code local: arduino-cli + core esp32 + libs, compile firmware, wokwi.toml, tasks.json, README - done
- [x] ses_8 (Worker): Brevo emails (asesor + auto T>27) + HVAC converge T + deploy VM - done (VERIFICADO por Reviewer ses_9)
- [x] ses_9 (Reviewer): Verificacion M1+M2 (S1.1.1-6, S2.1.1, S2.2.1-3) - done → TODO 10/10, ver .opencode/integration-status.md
- [x] ses_10 (Worker): FIX finding #1 - clamp /api/set-temp 16..32 + input HTML, deploy+verify VM - done

## File Status
| File | Action | Status | Session | Unit Test | Timestamp | Issue |
|------|--------|--------|---------|-----------|-----------|-------|
| python-vm-01.py | MODIFY (Brevo helper, HVAC physics, alerta auto T>27, boton asesor email, textos) | done | ses_8 | py_compile ok + AST ok + md5 local==remoto (81651aa5) + run.log sin traceback, T converge a setpoint | 2026-09-10T15:52:00 | - |
| .env (local) | MODIFY (append bloque EMAIL_* Brevo) | done | ses_8 | - | 2026-09-10T15:50:00 | - |
| VM: ~/taller_iot/.env | MODIFY (append bloque EMAIL_*, lineas existentes intactas) | done | ses_8 | cat .env verificado | 2026-09-10T15:51:00 | - |
| VM: python-vm-01.py | DEPLOY + RESTART (start.sh) | done | ses_8 | Conectado a IoT Central + telemetria fluyendo | 2026-09-10T15:52:00 | - |
| VM estado final | FIX (Commander): restaurar setpoint 16->22 tras prueba pendiente; +75s setpoint=22.0 T=24.0 Verde | done | ses_8 | GET /api/estado verificado | 2026-09-10T16:06:00 | - |
| python-vm-01.py | VERIFY (sin cambios) | done | ses_9 | py_compile+AST OK, md5==remoto, T 21.6→28.1 converge(sp 30), asesor T=30.6 + "OMITIDO", Traceback=0, setpoint restaurado 22.0 | 2026-09-10T15:59:00 | - |
| .opencode/integration-status.md | CREATE (evidencia M1/M2) | done | ses_9 | - | 2026-09-10T15:59:00 | - |
| python-vm-01.py | FIX (clamp api_set_temp 10..35 -> 16..32 DTDL, L262; input HTML min/max L121) | done | ses_10 | py_compile OK; md5 local==VM 8b2a31f7; live POST valor=10 => msg 16°C + GET set_temp_hvac=16; restaurado 22.0 | 2026-09-10T16:13:00 | Reviewer finding #1 |
| VM: python-vm-01.py | DEPLOY + RESTART (start.sh) post-fix | done | ses_10 | Conectado + Enviado fluyendo, grep -c Traceback = 0 | 2026-09-10T16:13:00 | - |
| python-vm-01.py | MODIFY (Flask) | done | ses_1 | compile ok + run ok | 2026-09-02T21:00:00 | - |
| requirements.txt | CREATE | done | ses_2 | pip install ok | 2026-09-02T20:49:00 | - |
| .gitignore | CREATE | done | ses_2 | - | 2026-09-02T20:50:00 | - |
| docs/bitacora.md | CREATE | done | ses_3 | - | 2026-09-02T21:09:00 | - |
| wokwi/sketch.ino | REWRITE (official full copy + DHT) | done | ses_4 | no stubs, API match verified | 2026-09-02T21:21:00 | - |
| wokwi/diagram.json | CREATE | done | ses_4 | - | 2026-09-02T21:05:00 | - |
| wokwi/libraries.txt | CREATE | done | ses_4 | - | 2026-09-02T21:05:00 | - |
| wokwi/iot_configs.h | MODIFY (pins PIN_DHT/PIN_POT/PIN_LED) | done | ses_4 | placeholders only, no secrets | 2026-09-02T21:17:00 | - |
| wokwi/AzureIoT.h | COPY (oficial, 858 ln) | done | ses_4 | verbatim del SDK | 2026-09-02T21:10:00 | - |
| wokwi/AzureIoT.cpp | COPY (oficial, 1492 ln) | done | ses_4 | verbatim del SDK | 2026-09-02T21:10:00 | - |
| wokwi/Azure_IoT_PnP_Template.h | COPY (oficial, 111 ln) | done | ses_4 | verbatim del SDK | 2026-09-02T21:19:00 | - |
| wokwi/Azure_IoT_PnP_Template.cpp | ADAPTED (DHT+pot telemetry, setAlertLed) | done | ses_4 | 497 ln, az_json_writer + 202/404 | 2026-09-02T21:20:00 | - |
| VM: python-vm-01.py | DEPLOY | done | ses_5 | run ok (Conectado a IoT Central) | 2026-09-02T20:55:00 | - |
| VM: dashboard :5000 | RUN | done | ses_5 | curl 200 + api/estado JSON | 2026-09-02T21:00:00 | - |
| wokwi/sketch.ino → wokwi.ino | RENAME | done | ses_7 | arduino-cli exige .ino==carpeta | 2026-09-03T13:00:00 | - |
| wokwi/build/wokwi.ino.merged.bin | BUILD | done | ses_7 | compile OK 80% flash/16% RAM | 2026-09-03T13:01:00 | - |
| wokwi/wokwi.toml | MODIFY | done | ses_7 | firmware→merged.bin + elf | 2026-09-03T13:01:00 | - |
| wokwi/.vscode/tasks.json | CREATE | done | ses_7 | Ctrl+Shift+B compila | 2026-09-03T13:02:00 | - |
| wokwi/README.md | CREATE | done | ses_7 | pasos licencia+compile+sim | 2026-09-03T13:03:00 | - |

## Notas
Todos los entregables del Laboratorio 2 están completos y verificados (TODO 41/41). S4.1.2 resuelto: usuario confirmó la Rule en el portal (2026-09-02 21:18). La próxima sesión cubrirá la ejecución del ESP32 en wokwi.com y la toma de capturas.

## Verificacion 2da pasada (Reviewer, 2026-09-10 ~16:09Z) — CONFIRMA PASS de ses_9
- Espejos todo.md IDENTICOS: md5 f9aa7173f42db57abb1827ad197276ae (root y taller_2_iot), 10/10 [x], 0 [ ], M1/M2 status completed. sync-issues.md vacio.
- Convergencia DESCENDENTE en vivo (evidencia mas fuerte, sp=16): T 21.6→19.8→19.3→18.7→17.9→17.6→17.3→16.8→16.8→16.4→16.3 (11 muestras ~15s c/u). run.log: `[Property writable] Set_temp_hvac actualizado desde web a 16.0` (lineas 54 y 98).
- Asesor (POST /api/llamar-asesor HTTP 200, msg con "correo via Brevo + Rule T>27"): T 16.3→27.3 (forzada 28.5-31 con decaimiento sp=22); run.log L132 `[Asesor] Temperatura forzada por encima de 27°C...` + L133 `[Email Brevo] OMITIDO: falta EMAIL_API_KEY en .env`; comandos: `Email Brevo asesor: omitido (sin llave o fallo)`. Traceback total = 0.
- Restauracion confirmada: GET final 16:09Z => set_temp_hvac=22.0, T=23.3, semaforo=Verde, id_salon=A-301 (app viva).
- Deploy: py_compile OK; md5 local == VM = 81651aa57ee74dfadf5199d9d56982bf; run.log `Conectado a IoT Central`=1, `Enviado:`=84. requirements.txt sin deps nuevas (Brevo via stdlib urllib).
- LSP: herramienta fallo (Rust process, no del codigo); sustituido por py_compile + AST + ejecucion real en VM.
- MISION VERIFICADA 100%: M1 (S1.1.1-6) + M2 (S2.1.1, S2.2.1-3) PASS.