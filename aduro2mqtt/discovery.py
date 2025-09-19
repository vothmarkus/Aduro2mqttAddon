
import os, json, time, re
import paho.mqtt.client as mqtt

BASE = os.getenv("MQTT_BASE_TOPIC", "aduro2mqtt").rstrip('/')
HOST = os.getenv("MQTT_BROKER_HOST", "core-mosquitto")
PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
USER = os.getenv("MQTT_USER") or None
PWD  = os.getenv("MQTT_PASSWORD") or None

DISC_PREFIX   = os.getenv("DISCOVERY_PREFIX", "homeassistant").rstrip('/')
DEVICE_NAME   = os.getenv("DEVICE_NAME", "Aduro H2")
DEVICE_ID     = os.getenv("DEVICE_ID", "aduro_h2")
DEBUG         = os.getenv("DISCOVERY_DEBUG", "false").lower() == "true"
DO_CLEANUP    = os.getenv("DISCOVERY_CLEANUP","false").lower() == "true"
AUTO_LEARN    = os.getenv("ENABLE_AUTO_LEARN","false").lower() == "true"
LEARN_SECS    = int(os.getenv("DISCOVERY_LEARN_SECONDS", "8"))
TOPICS        = [t.strip() for t in (os.getenv("DISCOVERY_TOPICS","status,operating,advanced,settings/+,consumption/#")).split(",") if t.strip()]

def log(msg):
    if DEBUG: print(f"[discovery] {msg}", flush=True)

def pub(client, topic, payload, retain=True):
    if isinstance(payload, dict):
        s = json.dumps(payload, ensure_ascii=False)
    else:
        s = payload
    log(f"publish {topic} -> {s if s else '<empty>'}")
    client.publish(topic, s, qos=0, retain=retain)

def make_sensor(client, uid_suffix, name, state_topic, value_template, unit=None, dev_class=None, state_class=None, icon=None):
    payload = {
        "name": name,
        "uniq_id": f"{DEVICE_ID}_{uid_suffix}",
        "stat_t": state_topic,
        "val_tpl": value_template,
        "dev": {"ids":[DEVICE_ID],"name":DEVICE_NAME,"mf":"Aduro","mdl":"via aduro2mqtt"}
    }
    if unit: payload["unit_of_meas"] = unit
    if dev_class: payload["dev_cla"] = dev_class
    if state_class: payload["stat_cla"] = state_class
    if icon: payload["ic"] = icon
    topic = f"{DISC_PREFIX}/sensor/{DEVICE_ID}_{uid_suffix}/config"
    pub(client, topic, payload)

def make_switch(client, uid_suffix, name, cmd_t, pl_on, pl_off):
    payload = {
        "name": name,
        "uniq_id": f"{DEVICE_ID}_{uid_suffix}",
        "cmd_t": cmd_t,
        "pl_on": pl_on,
        "pl_off": pl_off,
        "opt": True,
        "dev": {"ids":[DEVICE_ID],"name":DEVICE_NAME,"mf":"Aduro","mdl":"via aduro2mqtt"}
    }
    topic = f"{DISC_PREFIX}/switch/{DEVICE_ID}_{uid_suffix}/config"
    pub(client, topic, payload)

def make_select(client, uid_suffix, name, cmd_t, cmd_tpl, state_topic, value_template, options):
    payload = {
        "name": name,
        "uniq_id": f"{DEVICE_ID}_{uid_suffix}",
        "cmd_t": cmd_t,
        "cmd_tpl": cmd_tpl,
        "stat_t": state_topic,
        "val_tpl": value_template,
        "options": options,
        "dev": {"ids":[DEVICE_ID],"name":DEVICE_NAME,"mf":"Aduro","mdl":"via aduro2mqtt"}
    }
    topic = f"{DISC_PREFIX}/select/{DEVICE_ID}_{uid_suffix}/config"
    pub(client, topic, payload)

def cleanup_previous(client):
    target_prefix = f"{DISC_PREFIX}/"
    collected = set()
    def on_msg(_c, _u, msg):
        t = msg.topic
        if f"/{DEVICE_ID}_" in t and t.startswith(target_prefix) and t.endswith("/config"):
            collected.add(t)
    client.on_message = on_msg
    client.subscribe(f"{DISC_PREFIX}/#", qos=0)
    log("collecting retained discovery configs for cleanup ...")
    start = time.time()
    while time.time() - start < 2.5:
        client.loop(timeout=0.5)
    if collected:
        log(f"cleanup {len(collected)} topics")
        for t in collected:
            pub(client, t, "", retain=True)
            time.sleep(0.01)
    else:
        log("no old discovery topics found to cleanup")

def static_discovery(client):
    # Controls
    make_switch(
        client, "toggle", f"{DEVICE_NAME} toggle",
        f"{BASE}/set",
        '{"path": "misc.start", "value": "1"}',
        '{"path": "misc.stop",  "value": "1"}'
    )
    make_select(
        client, "fixed_power", f"{DEVICE_NAME} Fixed power (%)",
        f"{BASE}/set",
        '{"path": "regulation.fixed_power", "value": {{ value }} }',
        f"{BASE}/settings/regulation",
        "{{ value_json.fixed_power | int }}",
        ["10","50","100"]
    )

    # Static sensors
    S = f"{BASE}/status"
    C = f"{BASE}/consumption/counter"

    sensors = [
        ("room_temp",     f"{S}", "{{ value_json.boiler_temp | float }}", "°C", "temperature", "measurement", None),
        ("shaft_temp",    f"{S}", "{{ value_json.shaft_temp  | float }}", "°C", "temperature", "measurement", None),
        ("smoke_temp",    f"{S}", "{{ value_json.smoke_temp  | float }}", "°C", "temperature", "measurement", None),
        ("dhw_temp",      f"{S}", "{{ value_json.dhw_temp    | float }}", "°C", "temperature", "measurement", None),
        ("return_temp",   f"{S}", "{{ value_json.return_temp | float }}", "°C", "temperature", "measurement", None),
        ("power_pct",     f"{S}", "{{ value_json.power_pct   | float }}", "%",  None, "measurement", None),
        ("exhaust_speed", f"{S}", "{{ value_json.exhaust_speed | float }}", None, None, "measurement", None),
        ("oxygen",        f"{S}", "{{ value_json.oxygen      | float }}", "%",  None, "measurement", None),
        ("boiler_pump",   f"{S}", "{{ value_json.boiler_pump_state | int }}", None, None, None, None),
        ("state",         f"{S}", "{{ value_json.state | int }}", None, None, None, None),
        ("co",            f"{S}", "{{ value_json['drift.co'] | int }}", "ppm", "carbon_monoxide", "measurement", None),
        ("total_hours",   f"{C}", "{{ value_json[0] | float }}", "h", None, "total_increasing", None),
    ]

    for uid, topic, tpl, unit, devc, statec, icon in sensors:
        make_sensor(client, uid, f"{DEVICE_NAME} {uid.replace('_',' ').title()}", topic, tpl, unit, devc, statec, icon)

def auto_learn(client):
    seen = set()
    def on_message(_c, _u, msg):
        topic = msg.topic
        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            return
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    key_tpl = f"{{{{ value_json['{k}'] }}}}" if '.' in k else f"{{{{ value_json.{k} }}}}"
                    uid = re.sub(r"[^a-z0-9_]+","_", f"{topic.replace('/', '_')}_{k}".lower())
                    if uid in seen: 
                        continue
                    seen.add(uid)
                    make_sensor(client, uid, f"{DEVICE_NAME} {k.replace('_',' ').title()}", topic, key_tpl)
        elif isinstance(data, list):
            for idx, v in enumerate(data):
                if isinstance(v, (int, float)):
                    uid = re.sub(r"[^a-z0-9_]+","_", f"{topic.replace('/', '_')}_{idx}".lower())
                    make_sensor(client, uid, f"{DEVICE_NAME} {topic.split('/')[-1].title()} {idx}", topic, f"{{{{ value_json[{idx}] }}}}")
    client.on_message = on_message
    for t in [f"{BASE}/{t0}" for t0 in TOPICS]:
        print(f"[discovery] subscribe {t}")
        client.subscribe(t, qos=0)
    start = time.time()
    while time.time() - start < LEARN_SECS:
        client.loop(timeout=1.0)

def main():
    client = mqtt.Client(client_id=f"{DEVICE_ID}_disc", protocol=mqtt.MQTTv311)
    if USER:
        client.username_pw_set(USER, PWD)
    try:
        print(f"[discovery] connect mqtt host={HOST} port={PORT} user={'<set>' if USER else '<none>'}")
        client.connect(HOST, PORT, keepalive=30)
    except Exception as e:
        print(f"[discovery] MQTT connect failed: {e}")
        return

    print(f"[discovery] discovery_prefix={DISC_PREFIX} device={DEVICE_NAME}/{DEVICE_ID} base={BASE}")

    if DO_CLEANUP:
        cleanup_previous(client)

    static_discovery(client)

    if AUTO_LEARN:
        auto_learn(client)

    client.disconnect()
    print("[discovery] done")

if __name__ == "__main__":
    main()
