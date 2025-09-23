#!/usr/bin/env python3
import os, json, time, threading, subprocess, paho.mqtt.client as mqtt

BASE = os.getenv("MQTT_BASE_TOPIC", "aduro2mqtt")
MQTT_HOST = os.getenv("MQTT_HOST", "core-mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER") or os.getenv("MQTT_BROKER_USERNAME", "")
MQTT_PASS = os.getenv("MQTT_PASSWORD") or os.getenv("MQTT_BROKER_PASSWORD", "")
CLIENT_ID = (os.getenv("MQTT_CLIENT_ID") or "aduro2mqtt_refresh") + "_ref"

ADURO_HOST  = os.getenv("ADURO_HOST") or os.getenv("ADURO_BURNER_HOST", "")
ADURO_SERIAL= os.getenv("ADURO_SERIAL", "")
ADURO_PIN   = os.getenv("ADURO_PIN", "")

# Debounce, falls in kurzer Folge mehrere Befehle kommen
_debounce = None
def schedule_refresh(client, delay=0.6):
    global _debounce
    if _debounce and _debounce.is_alive():
        _debounce.cancel()
    _debounce = threading.Timer(delay, lambda: do_refresh(client))
    _debounce.daemon = True
    _debounce.start()

def _run_pyduro(*args):
    cmd = ["python3","-m","pyduro","-b",ADURO_HOST,"-s",ADURO_SERIAL,"-p",ADURO_PIN] + list(args)
    out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
    return json.loads(out.decode("utf-8"))

def do_refresh(client):
    try:
        # status
        try:
            st = _run_pyduro("status")
            client.publish(f"{BASE}/status", json.dumps(st), qos=0, retain=False)
        except Exception:
            pass

        # settings/regulation (fixed_power, operation_mode, …)
        try:
            reg = _run_pyduro("get","settings","regulation.*")
            client.publish(f"{BASE}/settings/regulation", json.dumps(reg), qos=0, retain=False)
        except Exception:
            pass

        # settings/boiler (boiler.temp = Raum-Soll)
        try:
            boil = _run_pyduro("get","settings","boiler.*")
            client.publish(f"{BASE}/settings/boiler", json.dumps(boil), qos=0, retain=False)
        except Exception:
            pass
    except Exception:
        pass

def on_connect(client, userdata, flags, rc):
    client.subscribe(f"{BASE}/set", qos=0)

def on_message(client, userdata, msg):
    # Jede erfolgreiche Nutzer-Änderung soll sofort frische States holen
    schedule_refresh(client, delay=0.6)

def main():
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    if MQTT_USER or MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_forever()

if __name__ == "__main__":
    main()
