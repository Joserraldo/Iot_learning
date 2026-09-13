# Guía — Encender y operar la VM de Azure (Laboratorio 2)

Proceso **cada vez que prendemos la VM** de Azure donde corre el nodo Python
(`python-vm-01.py`) + el dashboard Flask. Copiar/pegar en orden.

> **Secretos:** la contraseña de la VM **nunca** se guarda en el repo. Se pasa por
> variable de entorno `VM_PASS` en la sesión. `VM_HOST` y `VM_USER` no son secretos.

---

## 0. Datos fijos

| Dato | Valor |
|---|---|
| IP pública VM | `57.156.62.111` (se mantiene al apagar con **Stop/deallocate**) |
| Usuario SSH | `jtellez312` |
| Ruta remota del proyecto | `~/taller_iot/` |
| Script del nodo | `~/taller_iot/python-vm-01.py` |
| Arranque en background | `~/taller_iot/start.sh` → escribe `~/taller_iot/run.log` |
| Dashboard | **Público:** `http://57.156.62.111:5000` (NSG abre TCP/5000; túnel SSH sigue como alternativa) |
| Device IoT Central (VM) | `23z8rpgm6s4` (plantilla `consola-unab-ambiental`) |
| Correos de alerta | Brevo — `EMAIL_API_KEY` en `~/taller_iot/.env` (chmod 600, nunca en el repo) |

**Helpers** (en `tools/`, usan `paramiko`, credenciales por env):
- `vm_ssh.py "<comando bash>"` → ejecuta un comando en la VM.
- `vm_push.py <local> <remoto>` → sube un archivo (por base64, robusto con rutas).
- `vm_upload.py <local> <remoto>` → sube un archivo (por SFTP).
- `vm_restore.py [--dry-run]` → post-Reset-password: valida login, arranca el
  nodo si no corre, revisa `run.log` y el dashboard (`/api/estado`) en un solo paso.

---

## 1. Encender la VM (Portal de Azure)
1. Portal → **Virtual machines** → selecciona la VM → **Start**.
2. Espera ~1 min a que quede **Running**.
3. **Verifica la IP** en la hoja de la VM (debería seguir siendo `57.156.62.111`).
   - Si cambió (a veces pasa al hacer *deallocate* con IP dinámica), anótala y úsala en el paso 2.

## 2. Fijar credenciales en la sesión local
**Git-Bash (recomendado para estos comandos):**
```bash
export VM_HOST=57.156.62.111
export VM_USER=jtellez312
read -s VM_PASS && export VM_PASS   # escribe la clave, no se ve ni queda en historial
```
**PowerShell (alternativa):**
```powershell
$env:VM_HOST="57.156.62.111"; $env:VM_USER="jtellez312"; $env:VM_PASS=Read-Host "VM_PASS" -AsSecureString
# (más simple: usa Git-Bash arriba)
```

## 3. Probar conexión SSH
```bash
MSYS_NO_PATHCONV=1 python tools/vm_ssh.py "echo hola && hostname && uptime"
```
- `MSYS_NO_PATHCONV=1` evita que Git-Bash deforme rutas tipo `/home/...`.
- Si da timeout: la VM aún no está *Running* o el NSG no permite TCP/22 desde tu IP.

## 4. Arrancar el nodo + dashboard (si no están corriendo)
```bash
# ¿ya corre?
MSYS_NO_PATHCONV=1 python tools/vm_ssh.py "pgrep -af python-vm-01.py || echo NO-CORRE"

# arrancar en background (start.sh activa el venv y hace: python -u python-vm-01.py > run.log 2>&1 &)
MSYS_NO_PATHCONV=1 python tools/vm_ssh.py "bash ~/taller_iot/start.sh"

# ver logs (busca 'Conectado a IoT Central.' y telemetría cada 10 s)
MSYS_NO_PATHCONV=1 python tools/vm_ssh.py "tail -n 25 ~/taller_iot/run.log"
```

## 5. Ver el dashboard (ahora es público)

**Opción directa (la normal):** abre en el navegador
```
http://57.156.62.111:5000
```
- ⚠️ Escribe **`http://` completo**. Chrome fuerza `https://` al escribir solo la IP y Flask solo habla HTTP → parece que "no abre" (error de conexión, cuando el servidor está perfecto). Si Chrome insiste, Firefox.
- API de estado: `http://57.156.62.111:5000/api/estado`
- Endpoints de control: `POST /api/set-temp {"valor":22}` · `POST /api/force-reading` · `POST /api/llamar-asesor`

**Opción túnel SSH (fallback si el NSG se cierra):**
```bash
ssh -L 5000:localhost:5000 jtellez312@57.156.62.111   # → http://localhost:5000
# o: python tools/vm_tunnel.py --local 5000 --remote 5000
```

## 5.1 Correos de alerta (Brevo)

El nodo envía correos por su cuenta **además** de la Rule de IoT Central:

| Cuándo | Asunto |
|---|---|
| Botón *Llamar asesor* | `[LLAMADO] Asesor solicitado - Salon A-301` (inmediato, sin cooldown) |
| T cruza >27 °C (borde de subida) | `[ALERTA] Salon A-301: temperatura alta` (cooldown 10 min) |

**Configurar desde cero:**
1. [app.brevo.com](https://app.brevo.com) → cuenta free (300 correos/día).
2. Settings → **SMTP & API** → *Generate API key* (`xkeysib-...`).
3. Verifica el remitente en *Senders, domains & IPs* (si no, el correo puede caer en **spam**).
4. En la VM:
   ```bash
   python tools/vm_ssh.py "nano ~/taller_iot/.env"
   # EMAIL_API_KEY=xkeysib-...
   # EMAIL_REMITENTE=correo-verificado@...
   # EMAIL_DESTINATARIO=jtellez312@unab.edu.co
   python tools/vm_ssh.py "chmod 600 ~/taller_iot/.env && bash ~/taller_iot/start.sh"
   ```
5. Prueba: `POST /api/llamar-asesor` → en `run.log` debe aparecer
   `[Email Brevo] 201 OK messageId=<...@smtp-relay.mailin.fr>`.
   - `401` → llave inválida. `400` remitente no verificado. Sin llave → `OMITIDO` (la telemetría sigue igual).

## 6. Subir cambios de código (si editaste python-vm-01.py en local)
```bash
# 1) subir el archivo
MSYS_NO_PATHCONV=1 python tools/vm_push.py python-vm-01.py ~/taller_iot/python-vm-01.py
# 2) reiniciar el nodo
MSYS_NO_PATHCONV=1 python tools/vm_ssh.py "pkill -f python-vm-01.py; sleep 1; bash ~/taller_iot/start.sh"
# 3) verificar
MSYS_NO_PATHCONV=1 python tools/vm_ssh.py "tail -n 15 ~/taller_iot/run.log"
```

## 7. Apagar la VM al terminar (ahorra costos)
Portal → VM → **Stop** (deallocate). La IP pública se mantiene.
- Antes de apagar, opcional: `python tools/vm_ssh.py "pkill -f python-vm-01.py"` (se mata solo al apagar).

---

## Troubleshooting
- **"faltan VM_HOST/VM_USER/VM_PASS":** no exportaste las variables en esta terminal.
- **Timeout en SSH:** VM apagada o *Starting*; o tu IP pública cambió y el NSG la bloquea (Network security group → inbound rule TCP/22).
- **Dashboard no carga en :5000:** primero que sea `http://` (no https, paso 5). Luego revisa `run.log` (¿el Flask levantó? ¿el script murió?). Si el NSG cerró el puerto, usa el túnel del paso 5.
- **`start.sh` no existe en la VM:** se perdió (VM reimagen). Recrear:
  ```bash
  MSYS_NO_PATHCONV=1 python tools/vm_ssh.py "cat > ~/taller_iot/start.sh <<'EOF'
  #!/bin/bash
  cd ~/taller_iot
  source venv/bin/activate
  nohup python -u python-vm-01.py > run.log 2>&1 &
  echo 'nodo lanzado, PID='\$!
  EOF
  chmod +x ~/taller_iot/start.sh"
  ```
- **Dependencia local:** `paramiko` (ya en `.venv`, v5.0.0). Si falta: `pip install paramiko`.

## Resumen rápido (lo de siempre)
```bash
export VM_HOST=57.156.62.111 VM_USER=jtellez312; read -s VM_PASS && export VM_PASS
MSYS_NO_PATHCONV=1 python tools/vm_ssh.py "bash ~/taller_iot/start.sh"
MSYS_NO_PATHCONV=1 python tools/vm_ssh.py "tail -n 25 ~/taller_iot/run.log"
# dashboard: http://57.156.62.111:5000   (o túnel: ssh -L 5000:localhost:5000 jtellez312@57.156.62.111)
```
