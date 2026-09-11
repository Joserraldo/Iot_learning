# Integration Status — Brevo emails + HVAC setpoint converge (M1/M2)

Date: 2026-09-10T15:59Z | Verified by: ses_9 (Reviewer) | Verdict: **PASS — misión completa**

## Ambiente verificado
- VM 57.156.62.111, proceso vivo `./venv/bin/python -u python-vm-01.py` (PID 24943 al deploy).
- md5 local == remoto: `81651aa57ee74dfadf5199d9d56982bf`.
- `python -m py_compile python-vm-01.py` => OK; `ast.parse` => OK.
- LSP: no hay servidor Python disponible en este entorno (fallo de herramienta, no del codigo). Estatisco cubierto con py_compile + AST + ejecucion real en VM.
- `grep -c Traceback ~/taller_iot/run.log` => **0** (despues de todas las pruebas).
- EMAIL_API_KEY intencionalmente vacio => correos deben OMITIRSE sin romper telemetria (confirmado).

## Pruebas en vivo (evidencia citada)

### S2.2.1a — GET /api/estado externo
`HTTP 200` con JSON: `"set_temp_hvac":22.0`, `"telemetria":{"Humidity":55.0,"Iluminance":461.8,"Temperature":21.9}`, `historial` (40 pts), `comandos`, `"id_salon":"A-301"`, `"semaforo":"Verde"`.

### S2.2.1b — writable Set_temp_hvac converge T real (setpoint 30)
- POST /api/set-temp `{"valor":30}` => `{"msg":"Set_temp_hvac = 30.0°C enviado al dispositivo"}`
- run.log: `[Property writable] Set_temp_hvac actualizado desde web a 30.0`
- historial /api/estado (T vs ts): 21.6(15:55:46) → 22.6 → 23.8 → 24.6 → 25.3 → 26.1 → 26.8 → 27.6 → 28.0 → 28.1(15:57:21). Convergencia monotona ascendente factor 0.15/ciclo. **PASS**
- Descendente (prueba externa con setpoint 16): T 28.2 → 26.2 → ... → 22.2. Tambien converge.

### S2.2.1c — borde de subida automatico T>27
Al cruzar el umbral en la ramps anterior (T=27.6, 15:56:59) el log imprime
`[Email Brevo] OMITIDO: falta EMAIL_API_KEY en .env` => rama de alerta auto ejecutada via `asyncio.to_thread`.

### S2.2.2 — boton Llamar asesor
- POST /api/llamar-asesor => `{"msg":"📞 Asesor solicitado: correo via Brevo + Rule T>27 en Azure IoT Central."}`
- run.log 15:57:44: `[Asesor] Temperatura forzada por encima de 27°C para disparar Rule de email` + `[Email Brevo] OMITIDO: falta EMAIL_API_KEY en .env`
- Ciclo posterior sigue >27: `Enviado: {'Temperature': 30.6, ...}` (15:57:52) y `28.2` (15:58:02) => margen de varios ciclos para que la Rule de Azure IoT Central dispare.
- Sin excepcion con llave vacia (Traceback=0). **PASS**

### S2.2.3 — restauracion
- POST /api/set-temp `{"valor":22}` => msg confirmado; +32s GET: `set_temp_hvac=22.0`, `Temperature=22.2`, `semaforo=Verde`. **PASS**

### Item 5 — lista comandos del dashboard
`comandos` incluye las lineas esperadas:
```
15:57:52 📞 Email Brevo asesor: omitido (sin llave o fallo)
15:57:59 Set_temp_hvac (desde web) -> 16.0°C, pendiente de aplicar
15:58:02 Set_temp_hvac aplicado -> 16.0°C
15:58:44 Set_temp_hvac (desde web) -> 22.0°C, pendiente de aplicar
15:58:44 Set_temp_hvac aplicado -> 22.0°C
```

## Config / secretos
- `.env` local y VM contienen bloque `EMAIL_API_KEY=`, `EMAIL_REMITENTE=`, `EMAIL_DESTINATARIO=jtellez312@unab.edu.co`; lineas AZURE_*/INTERVALO/ID_SALON intactas en la VM.
- Sin secretos hardcodeados en `python-vm-01.py` (todo via `os.environ`). El .py no registra ningun nuevo secret en repo.

## Verificacion estatica de codigo (S1.1.x)
| Item | Lineas | Resultado |
|---|---|---|
| S1.1.1 helper Brevo stdlib + to_thread | 336-379, 543, 578 | OK |
| S1.1.2 convergencia 0.15 + clamp 16..32 | 428-430 | OK |
| S1.1.3 borde subida + cooldown 600s | 320, 332-333, 509, 563-582 | OK |
| S1.1.4 asesor inmediato + log comandos | 529-555 | OK |
| S1.1.5 texto /api/llamar-asesor | 292 | OK |
| S1.1.6 .env local + VM | archivos leidos | OK |

## Observaciones (no bloqueantes)
1. A las 15:57:59 se recibiò un `POST /api/set-temp {"valor":16}` que **no** provenia de esta verificacion (misma IP de salida, probablemente usuario en el navegador o sesion concurrente). Sin efecto negativo: sirvio como prueba extra de convergencia descendente. Setpoint final quedo en 22.0.
2. La rama "omitido" del correo auto no imprime el asunto (solo el helper imprime `messageId` en exito). Para auditoria futura seria util loggear el asunto tambien en el camino OMITIDO. Mejora opcional, no requerida por spec.
3. Brevo reales aun NO verificados end-to-end (llave vacia a proposito). Cuando el usuario ponga `EMAIL_API_KEY`, basta reiniciar `start.sh`; el camino 201 esta cubierto por el mismo helper.

## Sync issues
Ninguno. `sync-issues.md` no requiere entradas.

## Confirmacion 2da pasada (Reviewer independiente, 2026-09-10 16:09Z) — PASS
- Espejos `todo.md` identicos (md5 `f9aa7173f42db57abb1827ad197276ae`), 10/10 `[x]`, M1/M2 `status: completed`.
- **S2.2.1 (descendente, mas fuerte):** POST `/api/set-temp {"valor":16}` => T: 21.6, 19.8, 19.3, 18.7, 17.9, 17.6, 17.3, 16.8, 16.8, 16.4, **16.3** (11 muestras, sp fijo 16.0). run.log: `Set_temp_hvac actualizado desde web a 16.0` (L54, L98). Prueba de que la property writable mueve la T real.
- **S2.2.2:** POST `/api/llamar-asesor` HTTP 200 con msg `correo via Brevo + Rule T>27`; T salto 16.3 -> 27.3; run.log L132 `[Asesor] Temperatura forzada...` + L133 `[Email Brevo] OMITIDO: falta EMAIL_API_KEY en .env`; `comandos` incluye `Email Brevo asesor: omitido (sin llave o fallo)`; `grep -c Traceback` = **0**.
- **S2.2.3:** estado final 16:09Z => `set_temp_hvac=22.0`, `T=23.3`, `semaforo=Verde` (restaurado y vivo).
- **S2.1.1 (re-verificado):** `py_compile` OK; md5 local == VM `81651aa57ee74dfadf5199d9d56982bf`; run.log `Conectado a IoT Central`=1, `Enviado:`=84; requirements.txt sin deps nuevas.
- Veredicto final: **MISION PASS — 10/10 verificado**, cero sync issues, cero traceback.
