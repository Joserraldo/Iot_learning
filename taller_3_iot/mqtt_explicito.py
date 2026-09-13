# -*- coding: utf-8 -*-
"""
Laboratorio 3 — UNAB-Ambiental: CLIENTE MQTT EXPLICITO (paho-mqtt).
Abre la "caja negra": sin azure-iot-device. El programador construye a mano
lo que el SDK ocultaba en el Lab 2:

  * token SAS (HMAC-SHA256 con la primary key, solo en memoria),
  * TLS 8883 al hub de IoT Central (iotc-*.azure-devices.net),
  * username MQTT  {hostname}/{deviceId}/?api-version=...
  * password       = token SAS completo,
  * PUBLISH telemetria a devices/{deviceId}/messages/events/  (QoS elegible),
  * SUBSCRIBES gemelo/metodos/C2D, twin GET inicial y reported-properties,
  * latencia publish -> PUBACK (on_publish) y reconexion con backoff.

Cero secretos en stdout/log: la KEY y el SAS token NUNCA se imprimen.

Uso:
  python mqtt_explicito.py --duration 60 --qos 1 [--interval 10]
                           [--cut-at 25] [--log archivo.jsonl] [--dotenv ruta]
                           [--debug-packets]
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import random
import re
import socket
import ssl
import sys
import threading
import time
import urllib.parse

try:
    import paho.mqtt.client as mqtt
    from paho.mqtt.enums import CallbackAPIVersion
except ImportError:
    sys.exit("Falta paho-mqtt. Instala: pip install 'paho-mqtt>=2.1'")

API_VERSION = "2021-04-12"  # version MQTT recomendada por docs MS (SDK del Lab 2 usaba 2019-10-01)


# ---------------------------------------------------------------- auth SAS
def build_sas_token(hostname: str, device_id: str, primary_key_b64: str, ttl: int = 3600) -> str:
    """SharedAccessSignature sr={uri}&sig={sig}&se={exp} — misma formula que
    azure/iot/device/common/auth/sastoken.py (verificada en fuentes del SDK, Lab 3 Etapa 1)."""
    resource = urllib.parse.quote_plus(f"{hostname}/devices/{device_id}")
    expiry = int(time.time()) + ttl
    signing_key = base64.b64decode(primary_key_b64)
    digest = hmac.new(signing_key, f"{resource}\n{expiry}".encode("utf-8"), hashlib.sha256).digest()
    sig = urllib.parse.quote_plus(base64.b64encode(digest).decode("utf-8"))
    return f"SharedAccessSignature sr={resource}&sig={sig}&se={expiry}"


# ---------------------------------------------------------------- telemetria
estado = {"temperature": 24.0, "humidity": 50.0, "iluminance": 400.0}


def generar_lectura() -> dict:
    """Random-walk identico a python-vm-01.py:329-340 (Lab 2) para comparar manzanas con manzanas."""
    estado["temperature"] = round(min(32, max(16, estado["temperature"] + random.uniform(-0.6, 0.6))), 1)
    estado["humidity"] = round(min(70, max(35, estado["humidity"] + random.uniform(-1.5, 1.5))), 1)
    estado["iluminance"] = round(min(800, max(100, estado["iluminance"] + random.uniform(-20, 20))), 1)
    return {"Temperature": estado["temperature"],
            "Humidity": estado["humidity"],
            "Iluminance": estado["iluminance"]}


def utc_ts() -> str:
    return time.strftime("%H:%M:%S", time.gmtime()) + f".{int(time.time() % 1 * 1000):03d}Z"


# ---------------------------------------------------------------- cliente
class ClienteMQTTExplícito:
    def __init__(self, hostname, device_id, key, interval, qos, log_path,
                 debug_packets=False):
        self.hostname, self.device_id = hostname, device_id
        self.interval, self.qos = interval, qos
        self.log = open(log_path, "a", encoding="utf-8") if log_path else None
        self.lock = threading.Lock()
        self.pending = {}          # mid -> {"t0": float, "seq": int}
        self.rows = []             # estadisticas por publicacion
        self.n_sent = 0
        self.n_conn = 0
        self.received = []         # (topic, bytes, ts) de twin/metodos/c2d
        t_start = time.time()
        self.client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2,
                                  client_id=device_id, clean_session=False, protocol=mqtt.MQTTv311)
        # SAS SOLO en memoria; password se fija una vez (TTL 1 h suficiente para runs <150 s)
        self.client.username_pw_set(
            username=f"{hostname}/{device_id}/?api-version={API_VERSION}",
            password=build_sas_token(hostname, device_id, key))
        self.client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)  # verificacion cert contra store del SO
        self.client.reconnect_delay_set(min_delay=1, max_delay=10)  # backoff visible en prueba de corte
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        self.client.on_subscribe = self._on_subscribe
        self.client.on_message = self._on_message
        if debug_packets:
            # API verificada paho 2.1.0: propiedad publica on_log (client.py:2399),
            # invocada en _easy_log (client.py:3250) con buffer formateado. paho no
            # loguea password/SAS (CONNECT solo registra flags u/p, client.py:3548).
            self.client.on_log = self._on_log
        self.t_start = t_start

    # --- helpers de evidencia
    def _ev(self, obj):
        line = json.dumps(obj, ensure_ascii=False)
        msg = f"[{utc_ts()}] {line}"
        print(msg, flush=True)
        if self.log:
            self.log.write(line + "\n")
            self.log.flush()

    # --- callbacks (API v2 de paho 2.x)
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        self.n_conn += 1
        self._ev({"evt": "CONNACK", "n": self.n_conn, "rc": str(reason_code),
                  "session_present": str(flags)})
        if str(reason_code) not in ("Success", "0"):
            return
        subs = ["$iothub/twin/PATCH/properties/desired/#",
                "$iothub/twin/res/#",
                "$iothub/methods/POST/#",
                f"devices/{self.device_id}/messages/devicebound/#"]
        for t in subs:
            client.subscribe(t, qos=1)
        # Hipotesis inicial (tormentas de reconexion 13:22-13:29): $rid alfanumerico o
        # qos=1 en operaciones gemelo. REFUTADA empiricamente: la corrida 13:20 ($rid
        # alfanumerico, qos=1) tuvo 1 CONNACK limpio, y la corrida 13:26-13:29 (con este
        # fix) tuvo 21. Causa real: DOS procesos simultaneos con el MISMO client_id ->
        # el hub expulsa al anterior -> ciclo reconecta/expulsa. Regla: serializer.
        client.publish("$iothub/twin/GET/?$rid=1", "", qos=0)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self._ev({"evt": "DISCONNECT", "rc": str(reason_code),
                  "flags": str(disconnect_flags)})

    def _on_subscribe(self, client, userdata, mid, reason_codes, properties):
        self._ev({"evt": "SUBACK", "mid": mid, "granted": str(reason_codes)})

    def _on_log(self, client, userdata, paho_level, buf):
        """Captura flujo crudo de paquetes MQTT (solo lineas Sending/Received)."""
        if buf.startswith("Sending "):
            direction = "SEND"
        elif buf.startswith("Received "):
            direction = "RECV"
        else:
            return
        parts = buf.split()
        ptype = parts[1].rstrip("(") if len(parts) > 1 else "?"
        m = re.search(r"(?:Mid: |, m)(\d+)", buf)
        self._ev({"evt": "PACKET", "dir": direction, "type": ptype,
                  "mid": int(m.group(1)) if m else None})

    def _on_publish(self, client, userdata, mid, reason_code, properties):
        with self.lock:
            info = self.pending.pop(mid, None)
        if info:
            rtt_ms = round((time.time() - info["t0"]) * 1000, 1)
            self._ev({"evt": "PUBACK", "mid": mid, "seq": info["seq"], "rtt_ms": rtt_ms,
                      "rc": str(reason_code), "qos_eff": info.get("qos")})
            self.rows.append({"seq": info["seq"], "bytes": info["bytes"],
                              "t_pub": info["t_pub"], "t_ack": utc_ts(),
                              "rtt_ms": rtt_ms, "qos": info["qos"],
                              "gap_vs_cfg_s": info.get("gap")})

    def _on_message(self, client, userdata, message):
        topic = message.topic
        payload = message.payload
        item = {"evt": "MSG", "topic": topic, "bytes": len(payload), "ts": utc_ts()}
        try:
            item["json"] = json.loads(payload.decode("utf-8"))
        except Exception:
            pass
        self.received.append(item)
        if topic.startswith("$iothub/twin/res/"):
            self._ev({**item, "note": "respuesta GET gemelo (res/<status>/?$rid=init1)"})
        elif topic.startswith("$iothub/twin/PATCH/properties/desired/"):
            # ack PnP: reported con eco de las properties deseadas
            try:
                d = json.loads(payload.decode("utf-8"))
                ver = d.get("$version", 0)
                eco = {k: v for k, v in d.items() if not k.startswith("$")}
                eco["$version"] = ver
                client.publish("$iothub/twin/PATCH/properties/reported/?$rid=2",
                               json.dumps(eco), qos=0)
            except Exception:
                pass
            self._ev({**item, "note": "desired patch -> echoed a reported"})
        elif topic.startswith("$iothub/methods/POST/"):
            name = topic.split("/")[3]
            rid = topic.split("$rid=")[-1].split("&")[0] if "$rid=" in topic else "0"
            client.publish(f"$iothub/methods/res/200/?$rid={rid}",
                           json.dumps({"method": name, "ok": True,
                                       "handler": "mqtt_explicito.py (sin SDK)"}), qos=0)
            self._ev({**item, "note": f"metodo {name} -> response 200/$rid={rid}"})
        else:
            self._ev({**item, "note": "mensaje C2D (devicebound)"})

    # --- ciclo de publicacion
    def publish_telemetry(self):
        self.n_sent += 1
        payload = json.dumps(generar_lectura())
        b = payload.encode("utf-8")
        t0 = time.time()
        r = self.client.publish(f"devices/{self.device_id}/messages/events/", b, qos=self.qos)
        with self.lock:
            self.pending[r.mid] = {"t0": t0, "seq": self.n_sent, "bytes": len(b),
                                   "t_pub": utc_ts(), "qos": self.qos}
        self._ev({"evt": "PUBLISH", "seq": self.n_sent, "bytes": len(b),
                  "topic": f"devices/{self.device_id}/messages/events/", "qos": self.qos,
                  "rc": str(r.rc)})
        return t0

    def force_socket_cut(self):
        """Simulacion de corte de red sin admin (fallback D3): cierre brusco del TCP del cliente."""
        try:
            s = self.client._sock
            if s:
                s.shutdown(socket.SHUT_RDWR)
                s.close()
                self._ev({"evt": "CUT_SIMULADO", "nota": "socket cerrado a mano (equivalente a cable suelto)"})
        except Exception as e:
            self._ev({"evt": "CUT_ERROR", "tipo": type(e).__name__})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=int, default=60)
    ap.add_argument("--qos", type=int, default=1, choices=[0, 1, 2])
    ap.add_argument("--interval", type=int, default=None)
    ap.add_argument("--cut-at", type=int, default=None, metavar="N",
                    help="forzar corte de socket a los N segundos (prueba de reconexion)")
    ap.add_argument("--log", default=None)
    ap.add_argument("--dotenv", default=None, help="ruta a .env con credenciales (fuera del print)")
    ap.add_argument("--debug-packets", action="store_true",
                    help="opt-in: loguear flujo crudo SEND/RECV de paquetes MQTT "
                         "(handshake QoS2: PUBLISH/PUBREC/PUBREL/PUBCOMP)")
    args = ap.parse_args()

    if args.dotenv:
        from dotenv import load_dotenv
        load_dotenv(args.dotenv)
    host = os.environ.get("IOT_HUB_HOSTNAME") or os.environ.get("AZURE_IOT_HOSTNAME")
    dev = os.environ.get("DEVICE_ID") or os.environ.get("AZURE_DEVICE_ID")
    key = os.environ.get("DEVICE_PRIMARY_KEY") or os.environ.get("AZURE_PRIMARY_KEY")
    if not (host and dev and key):
        sys.exit("Faltan env vars: IOT_HUB_HOSTNAME, DEVICE_ID, DEVICE_PRIMARY_KEY (ver .env.example)")
    interval = args.interval or int(os.environ.get("INTERVALO_SEGUNDOS", "10"))
    id_salon = os.environ.get("ID_SALON", "A-301")

    c = ClienteMQTTExplícito(host, dev, key, interval, args.qos, args.log,
                             debug_packets=args.debug_packets)
    c._ev({"evt": "START", "qos": args.qos, "interval_s": interval,
           "duration_s": args.duration, "hostname": host, "device_id": dev,
           "api_version": API_VERSION, "tls": "TLSv1_2:8883"})
    c.client.connect(host, port=8883, keepalive=60)
    c.client.loop_start()
    t0 = time.time()
    gap = None
    try:
        while time.time() - t0 < args.duration:
            t_pub = c.publish_telemetry()
            # reported-properties al estilo Lab 2 (ID_salon por gemelo, NO por telemetria)
            if c.n_sent == 1:
                c.client.publish("$iothub/twin/PATCH/properties/reported/?$rid=3",
                                 json.dumps({"ID_salon": id_salon,
                                             "Estado_semaforo_LED": "Amarillo"}), qos=0)
            # dormir hasta el siguiente tick
            while time.time() - t_pub < interval:
                if args.cut_at and 0 < (time.time() - t0) - args.cut_at < 0.2:
                    c.force_socket_cut()
                    args.cut_at = None
                time.sleep(0.2)
            gap = round(time.time() - t0 - interval * c.n_sent, 2)
    except KeyboardInterrupt:
        c._ev({"evt": "INTERRUPT"})
    finally:
        time.sleep(2.5)  # dar tiempo a PUBACKs finales / reconexiones
        c.client.loop_stop()
        c.client.disconnect()
        time.sleep(0.5)
    # resumen
    rtts = [r["rtt_ms"] for r in c.rows]
    c._ev({"evt": "SUMMARY", "qos": args.qos, "publicados": c.n_sent,
           "acks": len(c.rows), "conexiones": c.n_conn,
           "rtt_ms_avg": round(sum(rtts) / len(rtts), 1) if rtts else None,
           "rtt_ms_min": min(rtts) if rtts else None, "rtt_ms_max": max(rtts) if rtts else None,
           "mensajes_recibidos": len(c.received),
           "tabla": c.rows})
    if c.log:
        c.log.close()


if __name__ == "__main__":
    main()
