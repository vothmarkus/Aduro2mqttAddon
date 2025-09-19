
#!/usr/bin/env python3
"""
Minimal MQTT Discovery publisher for Aduro2MQTT.

- Publishes HA Discovery configs for a fixed set of useful entities.
- Honors DISCOVERY_EXCLUDE (comma-separated uniq_ids or short keys)
  default: "boiler_pump_state,return_temp"
- Uses PAHO MQTT v1 API to keep compatibility with Home Assistant base images.
"""

import json
import os
import time
import paho.mqtt.client as mqtt

DISCOVERY_PREFIX = os.getenv("DISCOVERY_PREFIX", "homeassistant").strip()
BASE_TOPIC       = os.getenv("BASE_TOPIC", "aduro2mqtt").strip()
DEVICE_NAME      = os.getenv("DEVICE_NAME", "Aduro H2").strip()
DEVICE_ID        = os.getenv("DEVICE_ID", "aduro_h2").strip()
MQTT_HOST        = os.getenv("MQTT_HOST", "core-mosquitto").strip()
MQTT_PORT        = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER        = os.getenv("MQTT_USER")
MQTT_PASSWORD    = os.getenv("MQTT_PASSWORD")
EXCLUDE_RAW      = os.getenv("DISCOVERY_EXCLUDE", "boiler_pump_state,return_temp")

# normalize exclude list
EXCLUDE = set([e.strip().lower() for e in EXCLUDE_RAW.split(",") if e.strip()])

def client_connect() -> mqtt.Client:
    client = mqtt.Client(client_id=f"{DEVICE_ID}_disc")
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD or "")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    return client

def disc_topic(kind: str, object_id: str) -> str:
    # e.g. homeassistant/sensor/aduro_h2_room_temp/config
    return f"{DISCOVERY_PREFIX}/{kind}/{DEVICE_ID}_{object_id}/config"

def device_payload():
    return {"ids": [DEVICE_ID], "name": DEVICE_NAME, "mf": "Aduro", "mdl": "via aduro2mqtt"}

def publish_entity(client, kind, object_id, payload):
    full = disc_topic(kind, object_id)
    payload["uniq_id"] = f"{DEVICE_ID}_{object_id}"
    payload["dev"] = device_payload()
    client.publish(full, json.dumps(payload), retain=True)

def main():
    print(f"[discovery] prefix={DISCOVERY_PREFIX} base={BASE_TOPIC} device={DEVICE_NAME}/{DEVICE_ID}")
    print(f"[discovery] exclude={sorted(EXCLUDE)}")
    client = client_connect()

    # SWITCH: toggle start/stop
    if "toggle" not in EXCLUDE and "aduro_h2_toggle" not in EXCLUDE:
        publish_entity(client, "switch", "toggle", {
            "name": f"{DEVICE_NAME} Toggle",
            "cmd_t": f"{BASE_TOPIC}/set",
            "pl_on":  json.dumps({"path": "misc.start", "value": "1"}),
            "pl_off": json.dumps({"path": "misc.stop",  "value": "1"}),
            "opt": True
        })

    # SELECT: fixed power
    if "fixed_power" not in EXCLUDE:
        publish_entity(client, "select", "fixed_power", {
            "name": f"{DEVICE_NAME} Fixed power (%)",
            "cmd_t": f"{BASE_TOPIC}/set",
            "cmd_tpl": '{"path": "regulation.fixed_power", "value": {{ value }} }',
            "stat_t": f"{BASE_TOPIC}/settings/regulation",
            "val_tpl": "{{ value_json.fixed_power | int }}",
            "options": ["10","50","100"],
        })

    # SENSORS (key -> (name, state_topic, value_template, unit, device_class, state_class))
    sensors = {
        "room_temp":    (f"{DEVICE_NAME} Room Temp",   f"{BASE_TOPIC}/status", "{{ value_json.boiler_temp }}", "°C", "temperature", "measurement"),
        "shaft_temp":   (f"{DEVICE_NAME} Shaft Temp",  f"{BASE_TOPIC}/status", "{{ value_json.shaft_temp }}",  "°C", "temperature", "measurement"),
        "smoke_temp":   (f"{DEVICE_NAME} Smoke Temp",  f"{BASE_TOPIC}/status", "{{ value_json.smoke_temp }}",  "°C", "temperature", "measurement"),
        "total_hours":  (f"{DEVICE_NAME} Total Hours", f"{BASE_TOPIC}/consumption/counter", "{{ value_json[0] }}", "h", None, "total_increasing"),
        "co":           (f"{DEVICE_NAME} Co",          f"{BASE_TOPIC}/status", "{{ value_json.drift.co | int }}", "ppm", None, "measurement"),
        "oxygen":       (f"{DEVICE_NAME} Oxygen",      f"{BASE_TOPIC}/operating", "{{ value_json.oxygen }}", "%", None, "measurement"),
        "power_pct":    (f"{DEVICE_NAME} Power Pct",   f"{BASE_TOPIC}/status", "{{ value_json.power_pct }}", "%", None, "measurement"),
        "exhaust_speed":(f"{DEVICE_NAME} Exhaust Speed", f"{BASE_TOPIC}/status", "{{ value_json.exhaust_speed }}", "", None, "measurement"),
        # explicitly *not* wanted by default:
        "boiler_pump_state": (f"{DEVICE_NAME} Boiler Pump", f"{BASE_TOPIC}/operating", "{{ value_json.boiler_pump_state | int }}", "", None, None),
        "return_temp":  (f"{DEVICE_NAME} Return Temp", f"{BASE_TOPIC}/operating", "{{ value_json.return_temp }}", "°C", "temperature", "measurement"),
    }

    for key, (name, stat_t, val_tpl, unit, dev_cla, stat_cla) in sensors.items():
        if key.lower() in EXCLUDE:
            continue
        payload = {"name": name, "stat_t": stat_t, "val_tpl": val_tpl}
        if unit: payload["unit_of_meas"] = unit
        if dev_cla: payload["dev_cla"] = dev_cla
        if stat_cla: payload["stat_cla"] = stat_cla
        publish_entity(client, "sensor", key, payload)

    client.loop_start()
    time.sleep(1.0)
    client.loop_stop()
    client.disconnect()
    print("[discovery] done")

if __name__ == "__main__":
    main()
