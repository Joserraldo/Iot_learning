# Work Log

## Active Sessions
- [x] ses_1 (Worker): `python-vm-01.py` (nodo VM + Flask dashboard) - done
- [x] ses_2 (Worker): `requirements.txt` + `.gitignore` - done
- [x] ses_3 (Worker): `docs/bitacora.md` - done
- [x] ses_4 (Worker): `wokwi/` (sketch.ino, diagram.json, libraries.txt, iot_configs.h) - done
- [x] ses_5 (Worker): VM setup + run + dashboard verify - done
- [x] ses_6 (Reviewer): Full System Verification - done (todos los M1-M5 completos, S4.1.2 confirmado por usuario)
- [x] ses_7 (Worker): Wokwi→VS Code local: arduino-cli + core esp32 + libs, compile firmware, wokwi.toml, tasks.json, README - done

## File Status
| File | Action | Status | Session | Unit Test | Timestamp | Issue |
|------|--------|--------|---------|-----------|-----------|-------|
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