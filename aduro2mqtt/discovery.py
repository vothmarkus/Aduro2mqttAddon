import os, json, time, re
import paho.mqtt.client as mqtt

BASE = os.getenv("MQTT_BASE_TOPIC", "aduro2mqtt").rstrip('/')
HOST = os.getenv("MQTT_BROKER_HOST", "core-mosquitto")
PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
USER = os.getenv("MQTT_USER") or None
PWD  = os.getenv("MQTT_PASSWORD") or None

DISC_PREFIX = os.getenv("DISCOVERY_PREFIX", "homeassistant").rstrip('/')
DEVICE_NAME = os.getenv("DEVICE_NAME", "Aduro H2")
DEVICE_ID   = os.getenv("DEVICE_ID", "aduro_h2")
DEBUG       = os.getenv("DISCOVERY_DEBUG", "false").lower() == "true"
LEARN_SECS  = int(os.getenv("DISCOVERY_LEARN_SECONDS", "8"))
TOPICS      = [t.strip() for t in (os.getenv("DISCOVERY_TOPICS","status,operating,advanced,settings/+,consumption/#")).split(",") if t.strip()]
DO_CLEANUP  = os.getenv("DISCOVERY_CLEANUP","false").lower() == "true"

def log(msg): 
    if DEBUG: print(f"[discovery] {msg}", flush=True)

def pub(client, topic, payload, retain=True):
    if isinstance(payload, dict):
        s = json.dumps(payload, ensure_ascii=False)
    else:
        s = payload  # allow empty string for cleanup
    log(f"publish {topic} -> {s if s else '<empty>'}")
    client.publish(topic, s, qos=0, retain=retain)

def unit_and_class(key, topic=""):
    k = key.lower()
    if any(x in k for x in ["temp", "temperature"]): return "°C", "temperature", "measurement"
    if any(x in k for x in ["pressure", "_pa"]):     return "Pa", "pressure", "measurement"
    if any(x in k for x in ["power", "pct", "percent"]): return "%", None, "measurement"
    if any(x in k for x in ["rpm"]):                 return "rpm", None, "measurement"
    if any(x in k for x in ["hours", "_h"]):         return "h", None, "total_increasing" if "consumption" in topic else "measurement"
    return None, None, "measurement"

def slug(s): 
    return re.sub(r"[^a-z0-9_]+","_", s.lower())

def make_sensor(client, uid_suffix, name, state_topic, value_template, unit=None, dev_class=None, state_class=None):
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
    topic = f"{DISC_PREFIX}/sensor/{DEVICE_ID}_{uid_suffix}/config"
    pub(client, topic, payload)

def cleanup_previous(client):
    # Subscribe to all discovery topics, capture retained for our device_id, then clear them.
    target_prefix = f"{DISC_PREFIX}/"
    collected = set()
    def on_msg(_c, _u, msg):
        t = msg.topic
        if f"/{DEVICE_ID}_" in t and t.startswith(target_prefix) and t.endswith("/config"):
            collected.add(t)
    client.on_message = on_msg
    client.subscribe(f"{DISC_PREFIX}/#", qos=0)
    log("collecting retained discovery configs for cleanup ...")
    # Give broker a moment to send retained messages
    start = time.time()
    while time.time() - start < 2.5:
        client.loop(timeout=0.5)
    if collected:
        log(f"cleanup {len(collected)} topics")
        for t in collected:
            pub(client, t, "", retain=True)  # empty retained payload clears topic
            time.sleep(0.02)
    else:
        log("no old discovery topics found to cleanup")

def main():
    client = mqtt.Client(client_id=f"{DEVICE_ID}_disc", protocol=mqtt.MQTTv311)
    if USER:
        client.username_pw_set(USER, PWD)
    try:
        client.connect(HOST, PORT, keepalive=30)
    except Exception as e:
        log(f"MQTT connect failed: {e}")
        return

    if DO_CLEANUP:
        cleanup_previous(client)

    # Static entities: switch + select
    switch_payload = {
        "name": f"{DEVICE_NAME} toggle",
        "uniq_id": f"{DEVICE_ID}_toggle",
        "cmd_t": f"{BASE}/set",
        "pl_on":  '{"path": "misc.start", "value": "1"}',
        "pl_off": '{"path": "misc.stop",  "value": "1"}',
        "opt": True,
        "dev": {"ids":[DEVICE_ID],"name":DEVICE_NAME,"mf":"Aduro","mdl":"via aduro2mqtt"}
    }
    pub(client, f"{DISC_PREFIX}/switch/{DEVICE_ID}_toggle/config", switch_payload)

    select_payload = {
        "name": f"{DEVICE_NAME} Fixed power (%)",
        "uniq_id": f"{DEVICE_ID}_fixed_power",
        "cmd_t": f"{BASE}/set",
        "cmd_tpl": '{"path": "regulation.fixed_power", "value": {{ value }} }',
        "stat_t": f"{BASE}/settings/regulation",
        "val_tpl": "{{ value_json.fixed_power | int }}",
        "options": ["10","50","100"],
        "dev": {"ids":[DEVICE_ID],"name":DEVICE_NAME,"mf":"Aduro","mdl":"via aduro2mqtt"}
    }
    pub(client, f"{DISC_PREFIX}/select/{DEVICE_ID}_fixed_power/config", select_payload)

    # Dynamic learn
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
                    unit, dev_class, state_class = unit_and_class(k, topic)
                    uid = slug(f"{topic.replace('/', '_')}_{k}")
                    if uid in seen: 
                        continue
                    seen.add(uid)
                    nice_name = f"{DEVICE_NAME} {k.replace('_',' ').title()}"
                    make_sensor(client, uid, nice_name, topic, f"{{{{ value_json.{k} }}}}", unit, dev_class, state_class)
        elif isinstance(data, list):
            for idx, v in enumerate(data):
                if isinstance(v, (int, float)):
                    uid = slug(f"{topic.replace('/', '_')}_{idx}")
                    unit, dev_class, state_class = unit_and_class(f"idx{idx}", topic)
                    nice_name = f"{DEVICE_NAME} {topic.split('/')[-1].replace('_',' ').title()} {idx}"
                    make_sensor(client, uid, nice_name, topic, f"{{{{ value_json[{idx}] }}}}", unit, dev_class, state_class)

    client.on_message = on_message
    for t in TOPICS:
        t_full = f"{BASE}/{t}"
        log(f"subscribe {t_full}")
        client.subscribe(t_full, qos=0)

    start = time.time()
    while time.time() - start < LEARN_SECS:
        client.loop(timeout=1.0)

    basics = [
        ("room_temp",  f"{BASE}/status", "{{ value_json.boiler_temp }}", "°C", "temperature", "measurement"),
        ("shaft_temp", f"{BASE}/status", "{{ value_json.shaft_temp }}", "°C", "temperature", "measurement"),
        ("smoke_temp", f"{BASE}/status", "{{ value_json.smoke_temp }}", "°C", "temperature", "measurement"),
        ("total_hours", f"{BASE}/consumption/counter", "{{ value_json[0] }}", "h", None, "total_increasing"),
    ]
    for uid, stat_t, val_tpl, unit, devc, statc in basics:
        if uid not in seen:
            make_sensor(client, uid, f"{DEVICE_NAME} {uid.replace('_',' ').title()}", stat_t, val_tpl, unit, devc, statc)

    client.disconnect()
    log("done")

if __name__ == "__main__":
    main()
