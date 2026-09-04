"""
UNAB-Ambiental - Laboratorio 2
Nodo Python que corre dentro de una VM y publica telemetria/propiedades
hacia Azure IoT Central, usando aprovisionamiento automatico via DPS.

Requiere variables de entorno (ver .env):
    AZURE_ID_SCOPE
    AZURE_DEVICE_ID
    AZURE_PRIMARY_KEY

Modela la misma plantilla consola-unab-ambiental del Laboratorio 1:
  Telemetria : Temperature, Humidity, Iluminance
  Properties : ID_salon (auto), Estado_semaforo_LED (auto), Set_temp_hvac (writable)
  Commands   : Encender_hvac, force_reading
"""

import asyncio
import json
import os
import random
import threading
from datetime import datetime, timezone

from dotenv import load_dotenv
from azure.iot.device import MethodResponse
from azure.iot.device.aio import IoTHubDeviceClient, ProvisioningDeviceClient

from flask import Flask, jsonify, render_template_string, request

load_dotenv()

# ---------------------------------------------------------------------------
# Mini dashboard local (vista de depuracion; el gemelo digital real es el de
# Azure IoT Central). Corre en un hilo separado, no bloquea el loop asyncio.
# ---------------------------------------------------------------------------
HTML_PAGINA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>UNAB-Ambiental — Consola del salón</title>
<style>
  :root {
    --bg:#0b1220; --panel:#151e30; --panel2:#1b2740; --txt:#e2e8f0;
    --sub:#8fa3bf; --accent:#38bdf8; --ok:#22c55e; --warn:#f59e0b; --danger:#ef4444;
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:'Segoe UI', system-ui, sans-serif; background:var(--bg); color:var(--txt); min-height:100vh; }
  .topbar { background:linear-gradient(90deg,#0ea5e9,#6366f1); padding:14px 28px; display:flex; justify-content:space-between; align-items:center; }
  .topbar h1 { font-size:1.15rem; font-weight:700; }
  .topbar .meta { font-size:.8rem; opacity:.9; }
  .wrap { max-width:1100px; margin:0 auto; padding:24px; }
  .semaf-block { text-align:center; padding:20px; background:var(--panel); border-radius:16px; margin-bottom:20px; }
  .semaforo { display:inline-block; padding:10px 34px; border-radius:999px; font-size:1.3rem; font-weight:800; letter-spacing:.03em; }
  .semaforo.Verde   { background:var(--ok);     color:#06281a; box-shadow:0 0 30px rgba(34,197,94,.55); }
  .semaforo.Amarillo{ background:var(--warn);   color:#3b2b00; box-shadow:0 0 30px rgba(245,158,11,.55); }
  .semaforo.Rojo    { background:var(--danger); color:#2a0b0b; box-shadow:0 0 30px rgba(239,68,68,.6); animation:pulse 1s infinite; }
  @keyframes pulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.04)} }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:16px; margin-bottom:20px; }
  .card { background:var(--panel); border-radius:14px; padding:18px 20px; border:1px solid #24324a; }
  .card .label { font-size:.72rem; color:var(--sub); text-transform:uppercase; letter-spacing:.06em; }
  .card .valor { font-size:1.9rem; font-weight:800; margin-top:6px; }
  .card .unidad { font-size:.8rem; color:var(--sub); font-weight:400; }
  .panel { background:var(--panel); border-radius:14px; padding:20px; margin-bottom:20px; border:1px solid #24324a; }
  .panel h2 { font-size:.95rem; margin-bottom:12px; color:var(--sub); text-transform:uppercase; letter-spacing:.06em; }
  canvas { width:100%; height:180px; background:#0e1626; border-radius:10px; }
  .controls { display:flex; gap:14px; flex-wrap:wrap; align-items:end; }
  .field label { display:block; font-size:.75rem; color:var(--sub); margin-bottom:6px; }
  .field input[type=number] {
    background:#0e1626; color:var(--txt); border:1px solid #33415e; border-radius:8px;
    padding:10px 12px; font-size:1rem; width:150px;
  }
  button {
    background:var(--accent); color:#062a3a; border:none; border-radius:8px;
    padding:11px 18px; font-weight:700; font-size:.9rem; cursor:pointer; transition:.15s;
  }
  button:hover { filter:brightness(1.12); }
  button.sec { background:#24324a; color:var(--txt); }
  button.asesor { background:var(--danger); color:#2a0b0b; }
  .feedback { font-size:.8rem; margin-top:8px; min-height:1em; color:var(--sub); }
  .feedback.ok { color:var(--ok); } .feedback.err { color:var(--danger); }
  table { width:100%; border-collapse:collapse; font-size:.82rem; }
  td, th { padding:7px 10px; text-align:left; border-bottom:1px solid #24324a; }
  th { color:var(--sub); text-transform:uppercase; font-size:.7rem; letter-spacing:.05em; }
  .mono { font-family:ui-monospace, Menlo, monospace; color:#7dd3fc; }
  .statusbar { display:flex; gap:18px; flex-wrap:wrap; font-size:.78rem; color:var(--sub); margin-top:16px; }
  .statusbar b { color:var(--txt); }
</style>
</head>
<body>
  <div class="topbar">
    <h1>🏫 UNAB-Ambiental · Consola del salón</h1>
    <div class="meta">Origen: Nodo Python · VM (dispositivo real IoT Central)</div>
  </div>

  <div class="wrap">
    <div class="semaf-block">
      <div class="semaforo" id="sem">—</div>
      <div class="statusbar" style="justify-content:center;">
        <span>Salón: <b id="salon">—</b></span>
        <span>Última lectura: <b id="hora">—</b></span>
        <span>Estado: <b id="estadoConexion">—</b></span>
      </div>
    </div>

    <div class="grid">
      <div class="card"><div class="label">Temperature</div><div class="valor"><span id="temp">--</span> <span class="unidad">°C</span></div></div>
      <div class="card"><div class="label">Humidity</div><div class="valor"><span id="hum">--</span> <span class="unidad">%RH</span></div></div>
      <div class="card"><div class="label">Iluminance</div><div class="valor"><span id="lux">--</span> <span class="unidad">lux</span></div></div>
      <div class="card"><div class="label">Set_temp_hvac</div><div class="valor"><span id="hvac">--</span> <span class="unidad">°C</span></div></div>
    </div>

    <div class="panel"><h2>Historial (últimas 40 lecturas)</h2><canvas id="graf"></canvas></div>

    <div class="panel">
      <h2>Control remoto (property writable)</h2>
      <div class="controls">
        <div class="field">
          <label for="setInput">Nuevo Set_temp_hvac (°C)</label>
          <input type="number" id="setInput" step="0.5" min="10" max="35" value="22">
        </div>
        <button onclick="enviarSet()">Aplicar setpoint</button>
        <button class="sec" onclick="forzarLectura()">Forzar lectura</button>
        <button class="asesor" onclick="llamarAsesor()">📞 Llamar asesor</button>
      </div>
      <div class="feedback" id="feedback"></div>
    </div>

    <div class="panel">
      <h2>Últimos comandos recibidos</h2>
      <table><thead><tr><th>Hora (UTC)</th><th>Evento</th></tr></thead><tbody id="cmds"><tr><td colspan="2">Sin comandos aún</td></tr></tbody></table>
    </div>
  </div>

  <script>
    const INTERVALO = 5000;
    const MAX_PTOS = 40;

    function graf() {
      const c = document.getElementById('graf');
      const dpr = window.devicePixelRatio || 1;
      const w = c.parentElement.clientWidth - 40, h = 180;
      c.width = w * dpr; c.height = h * dpr;
      c.style.height = h + 'px';
      const ctx = c.getContext('2d');
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, w, h);
      ctx.strokeStyle = '#33415e'; ctx.lineWidth = 1;
      for (let i = 1; i < 4; i++) { ctx.beginPath(); ctx.moveTo(0, h*i/4); ctx.lineTo(w, h*i/4); ctx.stroke(); }
      return ctx;
    }

    function dibujar(hist) {
      const ctx = graf(); const w = ctx.canvas.width / (window.devicePixelRatio||1);
      const h = 180;
      const sers = [
        { key:'Temperature', min:16, max:32, color:'#38bdf8', label:'Temp' },
        { key:'Humidity', min:35, max:70, color:'#22c55e', label:'Hum' },
        { key:'Iluminance', min:100, max:800, color:'#f59e0b', label:'Lux' },
      ];
      ctx.font = '11px sans-serif';
      sers.forEach(s => {
        ctx.strokeStyle = s.color; ctx.lineWidth = 2; ctx.beginPath();
        hist.forEach((p, i) => {
          const x = (i / (MAX_PTOS - 1)) * w;
          const y = h - ((Math.min(Math.max(p[s.key], s.min), s.max) - s.min) / (s.max - s.min)) * (h - 24) - 12;
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.stroke();
        ctx.fillStyle = s.color; ctx.fillText(s.label, 6, sers.indexOf(s) === 0 ? 16 : sers.indexOf(s) * 20 + 6);
      });
    }

    async function cargar() {
      try {
        const r = await fetch('/api/estado');
        const d = await r.json();
        document.getElementById('temp').textContent = d.telemetria.Temperature.toFixed(1);
        document.getElementById('hum').textContent = d.telemetria.Humidity.toFixed(1);
        document.getElementById('lux').textContent = d.telemetria.Iluminance.toFixed(0);
        document.getElementById('hvac').textContent = d.set_temp_hvac.toFixed(1);
        document.getElementById('salon').textContent = d.id_salon;
        document.getElementById('hora').textContent = d.ultima_lectura || '—';
        const sem = document.getElementById('sem');
        sem.textContent = 'Semáforo: ' + d.semaforo;
        sem.className = 'semaforo ' + d.semaforo;
        const tb = document.getElementById('cmds');
        if (!d.comandos.length) {
          tb.innerHTML = '<tr><td colspan="2">Sin comandos aún</td></tr>';
        } else {
          tb.innerHTML = d.comandos.slice().reverse().map(c => '<tr><td class="mono">' + c.split(' ')[0] + '</td><td>' + c.split(' ').slice(1).join(' ') + '</td></tr>').join('');
        }
        if (d.historial && d.historial.length > 1) dibujar(d.historial);
      } catch (e) { console.error(e); }
    }

    async function post(url, body) {
      try {
        const r = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body||{}) });
        const d = await r.json();
        const fb = document.getElementById('feedback');
        fb.textContent = d.msg || 'OK';
        fb.className = 'feedback ok';
      } catch (e) {
        const fb = document.getElementById('feedback');
        fb.textContent = 'Error: ' + e; fb.className = 'feedback err';
      }
    }

    function enviarSet() { post('/api/set-temp', { valor: parseFloat(document.getElementById('setInput').value) }); }
    function forzarLectura() { post('/api/force-reading'); }
    function llamarAsesor() { post('/api/llamar-asesor'); }

    cargar();
    setInterval(cargar, INTERVALO);
  </script>
</body>
</html>
"""

# Estado compartido entre el hilo Flask y el loop asyncio
dashboard = {
    "telemetria": {"Temperature": 0.0, "Humidity": 0.0, "Iluminance": 0.0},
    "semaforo": "Verde",
    "set_temp_hvac": 22.0,
    "comandos": [],
    "historial": [],
    "ultima_lectura": "—",
    "pending_set_temp": None,      # accion pendiente: nuevo setpoint
    "pending_asesor": False,      # accion pendiente: llamar asesor (dispara rule email)
}
dashboard_lock = threading.Lock()

app = Flask(__name__)


@app.get("/")
def pagina():
    return render_template_string(HTML_PAGINA)


@app.get("/api/estado")
def api_estado():
    with dashboard_lock:
        return jsonify({
            "telemetria": dict(dashboard["telemetria"]),
            "semaforo": dashboard["semaforo"],
            "set_temp_hvac": dashboard["set_temp_hvac"],
            "comandos": list(dashboard["comandos"]),
            "historial": list(dashboard["historial"]),
            "ultima_lectura": dashboard["ultima_lectura"],
            "id_salon": ID_SALON,
        })


@app.post("/api/set-temp")
def api_set_temp():
    data = request.get_json(force=True)
    valor = float(data.get("valor", 22.0))
    # Acotar a rango razonable
    valor = round(min(35, max(10, valor)), 1)
    with dashboard_lock:
        dashboard["pending_set_temp"] = valor
        dashboard["comandos"].append(
            f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} Set_temp_hvac (desde web) -> {valor}°C, pendiente de aplicar"
        )
        dashboard["comandos"] = dashboard["comandos"][-5:]
    return jsonify({"msg": f"Set_temp_hvac = {valor}°C enviado al dispositivo"})


@app.post("/api/force-reading")
def api_force_reading():
    """Fuerza una lectura inmediata de telemetria (mismo que el comando force_reading)."""
    with dashboard_lock:
        dashboard["comandos"].append(
            f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} force_reading (desde web) -> encolado"
        )
        dashboard["comandos"] = dashboard["comandos"][-5:]
    return jsonify({"msg": "Lectura forzada encolada"})


@app.post("/api/llamar-asesor")
def api_llamar_asesor():
    """Dispara la Rule de email (Temperature > 27) forzando una lectura con temperatura alta."""
    with dashboard_lock:
        dashboard["pending_asesor"] = True
        dashboard["comandos"].append(
            f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} 📞 Asesor solicitado -> forzando T>27°C para email"
        )
        dashboard["comandos"] = dashboard["comandos"][-5:]
    return jsonify({"msg": "📞 Asesor notificado: se enviará un correo (Rule T>27)."})


def iniciar_dashboard(puerto: int = 5000):
    """Arranca el dashboard Flask en un hilo daemon (no bloquea asyncio)."""
    th = threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": puerto, "debug": False, "use_reloader": False}, daemon=True)
    th.start()
    print(f"[Dashboard local] http://0.0.0.0:{puerto} (hilo Flask en background)")


# ---------------------------------------------------------------------------
# Configuracion (nunca hardcodear secretos, siempre desde variables de entorno)
# ---------------------------------------------------------------------------
ID_SCOPE = os.environ["AZURE_ID_SCOPE"]
DEVICE_ID = os.environ["AZURE_DEVICE_ID"]
PRIMARY_KEY = os.environ["AZURE_PRIMARY_KEY"]
PROVISIONING_HOST = "global.azure-devices-provisioning.net"

INTERVALO_SEGUNDOS = int(os.environ.get("INTERVALO_SEGUNDOS", "10"))
ID_SALON = os.environ.get("ID_SALON", "A-301")

# Estado interno del "gemelo" simulado por el script
estado = {
    "temperature": 24.0,
    "humidity": 50.0,
    "iluminance": 400.0,
    "set_temp_hvac": 22.0,
}


def calcular_semaforo(temp: float) -> str:
    """Replica la logica de semaforo LED definida en el diseno conceptual."""
    if 20 <= temp <= 26:
        return "Verde"
    if 18 <= temp < 20 or 26 < temp <= 28:
        return "Amarillo"
    return "Rojo"


def generar_lectura() -> dict:
    """Camina aleatoriamente dentro de los rangos operativos del DTDL
    (16-32 C, 35-70 %RH, 100-800 lux) para que los datos sean coherentes,
    sin saltos irreales entre una lectura y la siguiente."""
    estado["temperature"] = round(min(32, max(16, estado["temperature"] + random.uniform(-0.6, 0.6))), 1)
    estado["humidity"] = round(min(70, max(35, estado["humidity"] + random.uniform(-1.5, 1.5))), 1)
    estado["iluminance"] = round(min(800, max(100, estado["iluminance"] + random.uniform(-20, 20))), 1)
    return {
        "Temperature": estado["temperature"],
        "Humidity": estado["humidity"],
        "Iluminance": estado["iluminance"],
    }


async def provisionar_dispositivo():
    """Aprovisiona el dispositivo via DPS y devuelve el hub asignado."""
    provisioning_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=PROVISIONING_HOST,
        registration_id=DEVICE_ID,
        id_scope=ID_SCOPE,
        symmetric_key=PRIMARY_KEY,
    )
    resultado = await provisioning_client.register()
    if resultado.status != "assigned":
        raise RuntimeError(f"Aprovisionamiento fallido: {resultado.status}")
    return resultado.registration_state.assigned_hub, resultado.registration_state.device_id


async def manejar_comandos(client: IoTHubDeviceClient):
    """Atiende Encender_hvac y force_reading (Commands sincronos)."""
    while True:
        request = await client.receive_method_request()
        print(f"[Comando recibido] {request.name} payload={request.payload}")

        if request.name == "Encender_hvac":
            estado["set_temp_hvac"] = 22.0
            await client.patch_twin_reported_properties({"Set_temp_hvac": estado["set_temp_hvac"]})
            with dashboard_lock:
                dashboard["set_temp_hvac"] = estado["set_temp_hvac"]
                dashboard["comandos"].append(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} Encender_hvac -> HVAC encendido (22C)")
                dashboard["comandos"] = dashboard["comandos"][-5:]
            respuesta = MethodResponse.create_from_method_request(
                request, 200, {"resultado": "HVAC encendido, set point 22C"}
            )

        elif request.name == "force_reading":
            lectura = generar_lectura()
            await client.send_message(json.dumps(lectura))
            with dashboard_lock:
                dashboard["comandos"].append(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} force_reading -> {lectura}")
                dashboard["comandos"] = dashboard["comandos"][-5:]
            respuesta = MethodResponse.create_from_method_request(
                request, 200, {"resultado": "Lectura forzada enviada", **lectura}
            )

        else:
            respuesta = MethodResponse.create_from_method_request(
                request, 404, {"resultado": "Comando no reconocido"}
            )

        await client.send_method_response(respuesta)


async def manejar_property_writable(client: IoTHubDeviceClient):
    """Escucha cambios en Set_temp_hvac (unica property writable) y confirma
    el cambio devolviendolo como reported property."""
    while True:
        patch = await client.receive_twin_desired_properties_patch()
        if "Set_temp_hvac" in patch:
            nuevo_valor = patch["Set_temp_hvac"]
            estado["set_temp_hvac"] = nuevo_valor
            print(f"[Property writable] Set_temp_hvac actualizado a {nuevo_valor}")
            await client.patch_twin_reported_properties({"Set_temp_hvac": nuevo_valor})
            with dashboard_lock:
                dashboard["set_temp_hvac"] = nuevo_valor
                dashboard["comandos"].append(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} Set_temp_hvac -> {nuevo_valor}")
                dashboard["comandos"] = dashboard["comandos"][-5:]


async def enviar_telemetria_periodica(client: IoTHubDeviceClient):
    """Publica las 3 variables cada N segundos, actualiza las 2 properties
    de solo lectura, aplica setpoint/asesor pendientes desde la web y guarda
    historial para el dashboard."""
    while True:
        # ---- Consumir acciones encoladas desde la web (hilo Flask) ----
        with dashboard_lock:
            setpoint_pendiente = dashboard["pending_set_temp"]
            dashboard["pending_set_temp"] = None
            asesor_pendiente = dashboard["pending_asesor"]
            dashboard["pending_asesor"] = False

        if setpoint_pendiente is not None:
            estado["set_temp_hvac"] = setpoint_pendiente
            print(f"[Property writable] Set_temp_hvac actualizado desde web a {setpoint_pendiente}")
            await client.patch_twin_reported_properties({"Set_temp_hvac": setpoint_pendiente})
            with dashboard_lock:
                dashboard["set_temp_hvac"] = setpoint_pendiente
                dashboard["comandos"].append(
                    f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} Set_temp_hvac aplicado -> {setpoint_pendiente}°C"
                )
                dashboard["comandos"] = dashboard["comandos"][-5:]

        if asesor_pendiente:
            # Forzar temperatura > 27 para que la Rule del correo se dispare
            estado["temperature"] = round(random.uniform(28.5, 31.0), 1)
            print("[Asesor] Temperatura forzada por encima de 27°C para disparar Rule de email")

        lectura = generar_lectura()
        await client.send_message(json.dumps(lectura))
        print(f"[{datetime.now(timezone.utc).isoformat()}] Enviado: {lectura}")

        semaforo = calcular_semaforo(lectura["Temperature"])
        await client.patch_twin_reported_properties(
            {"ID_salon": ID_SALON, "Estado_semaforo_LED": semaforo}
        )
        ahora = datetime.now(timezone.utc).strftime("%H:%M:%S")
        with dashboard_lock:
            dashboard["telemetria"] = dict(lectura)
            dashboard["semaforo"] = semaforo
            dashboard["ultima_lectura"] = ahora
            dashboard["historial"].append({**lectura, "ts": ahora})
            dashboard["historial"] = dashboard["historial"][-40:]

        await asyncio.sleep(INTERVALO_SEGUNDOS)


async def main():
    # El dashboard Flask se inicia ANTES que el client, en hilo aparte
    iniciar_dashboard(puerto=int(os.environ.get("FLASK_PUERTO", "5000")))

    print("Aprovisionando dispositivo via DPS...")
    assigned_hub, device_id = await provisionar_dispositivo()
    print(f"Asignado a hub: {assigned_hub}")

    client = IoTHubDeviceClient.create_from_symmetric_key(
        symmetric_key=PRIMARY_KEY,
        hostname=assigned_hub,
        device_id=device_id,
    )
    await client.connect()
    print("Conectado a IoT Central.")

    await asyncio.gather(
        enviar_telemetria_periodica(client),
        manejar_comandos(client),
        manejar_property_writable(client),
    )


if __name__ == "__main__":
    asyncio.run(main())