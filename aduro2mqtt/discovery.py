#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aduro2mqttAddon MQTT Discovery publisher

Publishes (retain) the following Home Assistant discovery entities:
  A) Select: "Power / Temp" with options ["10","50","100","Fixed Temp"]
     - "Fixed Temp" -> sets regulation.operation_mode = 1 (temperature regulation)
     - numeric values -> sets regulation.fixed_power
  B) Climate: modes off/heat; target = boiler.ref; current temp = room_temp fallback boiler_temp
  C) Number (optional): Force Auger seconds (0..120 step 5)
"""
import json, os, time
import paho.mqtt.client as mqtt

# From run.sh / Add-on config
DISCOVERY_PREFIX = os.getenv("DISCOVERY_PREFIX", "homeassistant").strip()
BASE_TOPIC       = os.getenv("BASE_TOPIC", "aduro2mqtt").strip()
DEVICE_NAME      = os.getenv("DEVICE_NAME", "Aduro H2").strip()
DEVICE_ID        = os.getenv("DEVICE_ID", "aduro_h2").strip()

MQTT_HOST        = os.getenv("MQTT_HOST", "core-mosquitto").strip()
MQTT_PORT        = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER        = os.getenv("MQTT_USER")
MQTT_PASSWORD    = os.getenv("MQTT_PASSWORD")

# Aduro H2 temperature mode id
TEMP_MODE_VALUE  = 1

DEVICE = {
    "identifiers": [DEVICE_ID],
    "name": DEVICE_NAME,
    "manufacturer": "Aduro",
    "model": "via aduro2mqtt"
}

def disc_topic(kind: str, object_id: str) -> str:
    if kind == "climate":
        return f"{DISCOVERY_PREFIX}/{kind}/{DEVICE_ID}/config"
    return f"{DISCOVERY_PREFIX}/{kind}/{DEVICE_ID}_{object_id}/config"

def mqtt_connect() -> mqtt.Client:
    client = mqtt.Client(client_id=f"{DEVICE_ID}_disc")
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD or "")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    return client

def publish(client: mqtt.Client, topic: str, payload: dict) -> None:
    payload.setdefault("device", DEVICE)
    payload.setdefault("unique_id", payload.get("uniq_id", f"{DEVICE_ID}_{int(time.time())}"))
    if topic.endswith("/climate/" + DEVICE_ID + "/config"):
        payload["unique_id"] = f"{DEVICE_ID}_climate"
    client.publish(topic, json.dumps(payload, ensure_ascii=False, separators=(",", ":")), qos=1, retain=True)

def publish_select(client: mqtt.Client):
    topic = disc_topic("select", "power")
    cmd_tpl = (
        "{% if value == 'Fixed Temp' %}"
        "{{\"path\":\"regulation.operation_mode\",\"value\":" + str(TEMP_MODE_VALUE) + "}}"
        "{% else %}"
        "{{\"path\":\"regulation.fixed_power\",\"value\": {{ value|int }} }}"
        "{% endif %}"
    )
    val_tpl = (
        "{{ 'Fixed Temp' if (value_json.operation_mode|int) == " + str(TEMP_MODE_VALUE) +
        " else ((value_json.fixed_power|int) ~ '') }}"
    )
    payload = {
        "name": f"{DEVICE_NAME} Power / Temp",
        "uniq_id": f"{DEVICE_ID}_power",
        "command_topic": f"{BASE_TOPIC}/set",
        "command_template": cmd_tpl,
        "state_topic": f"{BASE_TOPIC}/settings/regulation",
        "value_template": val_tpl,
        "options": ["10","50","100","Fixed Temp"],
    }
    publish(client, topic, payload)

def publish_climate(client: mqtt.Client):
    topic = disc_topic("climate", "")
    payload = {
        "name": DEVICE_NAME,
        "uniq_id": f"{DEVICE_ID}_climate",
        "modes": ["off", "heat"],
        "mode_command_topic": f"{BASE_TOPIC}/set",
        "mode_command_template": (
            "{% if value == 'off' %}{\"path\":\"misc.stop\",\"value\":\"1\"}"
            "{% else %}{\"path\":\"misc.start\",\"value\":\"1\"}{% endif %}"
        ),
        "mode_state_topic": f"{BASE_TOPIC}/status",
        "mode_state_template": "{{ 'heat' if (value_json.state_super|int) == 1 else 'off' }}",
        "temperature_command_topic": f"{BASE_TOPIC}/set",
        "temperature_command_template": "{\"path\":\"boiler.ref\",\"value\": {{ value|float }} }",
        "temperature_state_topic": f"{BASE_TOPIC}/operating",
        "temperature_state_template": "{{ value_json.boiler_ref|float }}",
        "current_temperature_topic": f"{BASE_TOPIC}/status",
        "current_temperature_template": "{{ (value_json.room_temp | default(value_json.boiler_temp)) | float }}",
        "temperature_unit": "C",
        "min_temp": 10,
        "max_temp": 30,
        "temp_step": 0.5
    }
    publish(client, topic, payload)

def publish_force_auger(client: mqtt.Client):
    topic = disc_topic("number", "force_auger")
    payload = {
        "name": f"{DEVICE_NAME} Force Auger (s)",
        "uniq_id": f"{DEVICE_ID}_force_auger",
        "command_topic": f"{BASE_TOPIC}/set",
        "command_template": "{\"path\":\"auger.forced_run\",\"value\": {{ value|int }} }",
        "state_topic": f"{BASE_TOPIC}/settings/auger",
        "value_template": "{{ value_json.forced_run|int if value_json.forced_run is defined else 0 }}",
        "min": 0, "max": 120, "step": 5
    }
    publish(client, topic, payload)

def main():
    print(f"[discovery] mqtt={MQTT_HOST}:{MQTT_PORT} user={'<set>' if MQTT_USER else '<none>'}")
    print(f"[discovery] prefix={DISCOVERY_PREFIX} device={DEVICE_NAME}/{DEVICE_ID} base={BASE_TOPIC}")
    client = mqtt_connect()
    client.loop_start()
    publish_select(client)
    publish_climate(client)
    publish_force_auger(client)
    time.sleep(0.4)
    client.loop_stop()
    client.disconnect()
    print("[discovery] done")

if __name__ == "__main__":
    main()
