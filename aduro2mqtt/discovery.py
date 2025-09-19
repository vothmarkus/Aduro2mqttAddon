import os, json, time
import paho.mqtt.client as mqtt

BASE = os.getenv("MQTT_BASE_TOPIC", "aduro2mqtt")
HOST = os.getenv("MQTT_BROKER_HOST", "core-mosquitto")
PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
USER = os.getenv("MQTT_USER") or None
PWD  = os.getenv("MQTT_PASSWORD") or None

DISC_PREFIX = os.getenv("DISCOVERY_PREFIX", "homeassistant").rstrip('/')
DEVICE_NAME = os.getenv("DEVICE_NAME", "Aduro H2")
DEVICE_ID   = os.getenv("DEVICE_ID", "aduro_h2")
DEBUG       = os.getenv("DISCOVERY_DEBUG", "false").lower() == "true"

def log(msg):
    print(f"[discovery] {msg}", flush=True)

def pub(client, topic, payload):
    s = json.dumps(payload, ensure_ascii=False)
    if DEBUG: log(f"publish {topic} -> {s}")
    client.publish(topic, s, qos=0, retain=True)

def main():
    if DEBUG:
        log(f"connect mqtt host={HOST} port={PORT} user={'<set>' if USER else '<none>'}")
        log(f"discovery_prefix={DISC_PREFIX} device={DEVICE_NAME}/{DEVICE_ID} base={BASE}")

    # paho-mqtt <2.0 API
    client = mqtt.Client(client_id=f"{DEVICE_ID}_disc", protocol=mqtt.MQTTv311)
    if USER:
        client.username_pw_set(USER, PWD)

    try:
        client.connect(HOST, PORT, keepalive=30)
    except Exception as e:
        log(f"MQTT connect failed: {e}")
        return

    device = {"ids": [DEVICE_ID], "name": DEVICE_NAME, "mf": "Aduro", "mdl": "via aduro2mqtt"}

    sensors = [
        ("smoke_temp",  "Aduro H2 Smoke temperature",  f"{BASE}/status",               "{{ value_json.smoke_temp }}",  "°C", "temperature", "measurement"),
        ("shaft_temp",  "Aduro H2 Shaft temperature",  f"{BASE}/status",               "{{ value_json.shaft_temp }}",  "°C", "temperature", "measurement"),
        ("total_hours", "Aduro H2 Total hours",        f"{BASE}/consumption/counter",  "{{ value_json[0] }}",          "h",  None,         "total_increasing"),
        ("room_temp",   "Aduro H2 Room temperature",   f"{BASE}/status",               "{{ value_json.boiler_temp }}", "°C", "temperature", "measurement"),
    ]

    for uid, name, stat_t, val_tpl, unit, dev_cla, stat_cla in sensors:
        payload = {
            "name": name,
            "uniq_id": f"{DEVICE_ID}_{uid}",
            "stat_t": stat_t,
            "val_tpl": val_tpl,
            "dev": device
        }
        if unit: payload["unit_of_meas"] = unit
        if dev_cla: payload["dev_cla"] = dev_cla
        if stat_cla: payload["stat_cla"] = stat_cla
        topic = f"{DISC_PREFIX}/sensor/{DEVICE_ID}_{uid}/config"
        pub(client, topic, payload)

    switch_payload = {
        "name": "Aduro H2 toggle",
        "uniq_id": f"{DEVICE_ID}_toggle",
        "cmd_t": f"{BASE}/set",
        "pl_on":  '{"path": "misc.start", "value": "1"}',
        "pl_off": '{"path": "misc.stop",  "value": "1"}',
        "opt": True,
        "dev": device
    }
    pub(client, f"{DISC_PREFIX}/switch/{DEVICE_ID}_toggle/config", switch_payload)

    select_payload = {
        "name": "Aduro H2 Fixed power (%)",
        "uniq_id": f"{DEVICE_ID}_fixed_power",
        "cmd_t": f"{BASE}/set",
        "cmd_tpl": '{"path": "regulation.fixed_power", "value": {{ value }} }',
        "stat_t": f"{BASE}/settings/regulation",
        "val_tpl": "{{ value_json.fixed_power | int }}",
        "opts": ["10","50","100"],
        "dev": device
    }
    pub(client, f"{DISC_PREFIX}/select/{DEVICE_ID}_fixed_power/config", select_payload)

    for _ in range(3):
        client.loop(timeout=1.0)
        time.sleep(0.2)
    client.disconnect()
    if DEBUG: log("done")

if __name__ == "__main__":
    main()
