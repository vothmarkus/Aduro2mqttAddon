#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aduro2mqttAddon MQTT Discovery

- climate (hvac_modes: off/heat) mit preset_modes:
  * "Temperature" -> regulation.operation_mode = 1
  * "Power 10/50/100" -> regulation.fixed_power = 10/50/100
  * target temperature: boiler.ref (STATE aus settings/boiler.ref)
  * current temperature: room_temp (Fallback boiler_temp)

- number: Force Auger (s)

- sensors (mit DISCOVERY_EXCLUDE-Filter, komma-separiert):
  room_temp, boiler_temp, state_super, boiler_ref, operation_mode, fixed_power
"""

import os, json, time
from typing import Dict, Any, List
import paho.mqtt.client as mqtt

# ---- ENV aus run.sh / Add-on-Optionen ----
DISCOVERY_PREFIX = os.getenv("DISCOVERY_PREFIX", "homeassistant").strip()
BASE_TOPIC       = os.getenv("BASE_TOPIC", "aduro2mqtt").strip()
DEVICE_NAME      = os.getenv("DEVICE_NAME", "Aduro H2").strip()
DEVICE_ID        = os.getenv("DEVICE_ID", "aduro_h2").strip()

MQTT_HOST        = os.getenv("MQTT_HOST", "core-mosquitto").strip()
MQTT_PORT        = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER        = os.getenv("MQTT_USER") or os.getenv("MQTT_USERNAME")
MQTT_PASSWORD    = os.getenv("MQTT_PASSWORD", "")

# DISCOVERY_EXCLUDE z.B.: "boiler_pump_state,return_temp"
EXCLUDE_RAW      = (os.getenv("DISCOVERY_EXCLUDE") or "").strip()
EXCLUDE_SET      = set([s.strip() for s in EXCLUDE_RAW.split(",") if s.strip()])

TEMP_MODE_VALUE  = 1  # Aduro H2: Temperaturregelung = 1

DEVICE = {
    "identifiers": [DEVICE_ID],
    "name": DEVICE_NAME,
    "manufacturer": "Aduro",
    "model": "via aduro2mqtt",
}

def disc_topic(kind: str, object_id: str = "") -> str:
    """Home Assistant MQTT Discovery topic."""
    if object_id:
        return f"{DISCOVERY_PREFIX}/{kind}/{object_id}/config"
    # climate bekommt <DEVICE_ID> direkt
    return f"{DISCOVERY_PREFIX}/{kind}/{DEVICE_ID}/config"

def mqtt_connect() -> mqtt.Client:
    c = mqtt.Client(client_id=f"{DEVICE_ID}_disc")
    if MQTT_USER:
        c.username_pw_set(MQTT_USER, MQTT_PASSWORD or "")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    return c

def publish_config(client: mqtt.Client, topic: str, payload: Dict[str, Any]) -> None:
    payload.setdefault("device", DEVICE)
    j = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    client.publish(topic, j, qos=1, retain=True)

# ------------- CLIMATE -------------
def build_climate_payload() -> Dict[str, Any]:
    preset_cmd = (
        "{% if value in ['Temperature'] %}"
        "{{\"path\":\"regulation.operation_mode\",\"value\":" + str(TEMP_MODE_VALUE) + "}}"
        "{% elif value == 'Power 10' %}"
        "{{\"path\":\"regulation.fixed_power\",\"value\":10}}"
        "{% elif value == 'Power 50' %}"
        "{{\"path\":\"regulation.fixed_power\",\"value\":50}}"
        "{% elif value == 'Power 100' %}"
        "{{\"path\":\"regulation.fixed_power\",\"value\":100}}"
        "{% endif %}"
    )
    preset_state = (
        "{{ 'Temperature' if (value_json.operation_mode|int) == " + str(TEMP_MODE_VALUE) +
        " else ('Power ' ~ (value_json.fixed_power|int)) }}"
    )

    return {
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

        "preset_modes": ["Temperature","Power 10","Power 50","Power 100"],
        "preset_mode_command_topic": f"{BASE_TOPIC}/set",
        "preset_mode_command_template": preset_cmd,
        "preset_mode_state_topic": f"{BASE_TOPIC}/settings/regulation",
        "preset_mode_state_template": preset_state,

        "temperature_command_topic": f"{BASE_TOPIC}/set",
        "temperature_command_template": "{\"path\":\"boiler.ref\",\"value\": {{ value|float }} }",
        "temperature_state_topic": f"{BASE_TOPIC}/settings/boiler",
        "temperature_state_template": "{{ value_json.ref|float }}",

        "current_temperature_topic": f"{BASE_TOPIC}/status",
        "current_temperature_template": "{{ (value_json.room_temp | default(value_json.boiler_temp)) | float }}",

        "temperature_unit": "C",
        "min_temp": 10,
        "max_temp": 30,
        "temp_step": 0.5,
    }

# ------------- NUMBER (Force Auger) -------------
def build_force_auger_payload() -> Dict[str, Any]:
    return {
        "name": f"{DEVICE_NAME} Force Auger (s)",
        "uniq_id": f"{DEVICE_ID}_force_auger",
        "command_topic": f"{BASE_TOPIC}/set",
        "command_template": "{\"path\":\"auger.forced_run\",\"value\": {{ value|int }} }",
        "state_topic": f"{BASE_TOPIC}/settings/auger",
        "value_template": "{{ value_json.forced_run|int if value_json.forced_run is defined else 0 }}",
        "min": 0, "max": 120, "step": 5,
        "device": DEVICE,
    }

# ------------- SENSORS -------------
def sensor(kind: str, key: str, name: str, state_topic: str, value_template: str,
           unit: str = None, device_class: str = None, icon: str = None,
           state_class: str = None) -> Dict[str, Any]:
    p = {
        "name": name,
        "uniq_id": f"{DEVICE_ID}_{key}",
        "state_topic": state_topic,
        "value_template": value_template,
        "device": DEVICE,
    }
    if unit: p["unit_of_measurement"] = unit
    if device_class: p["device_class"] = device_class
    if icon: p["icon"] = icon
    if state_class: p["state_class"] = state_class
    return p

def build_sensors() -> List[Dict[str, Any]]:
    items = []

    # status: room_temp, boiler_temp, state_super
    if "room_temp" not in EXCLUDE_SET:
        items.append(("sensor", f"{DEVICE_ID}_room_temp",
                      sensor("sensor", "room_temp", f"{DEVICE_NAME} Room Temperature",
                             f"{BASE_TOPIC}/status", "{{ value_json.room_temp|float }}",
                             "°C", "temperature", None, "measurement")))

    if "boiler_temp" not in EXCLUDE_SET:
        items.append(("sensor", f"{DEVICE_ID}_boiler_temp",
                      sensor("sensor", "boiler_temp", f"{DEVICE_NAME} Boiler Temperature",
                             f"{BASE_TOPIC}/status", "{{ value_json.boiler_temp|float }}",
                             "°C", "temperature", None, "measurement")))

    if "state_super" not in EXCLUDE_SET:
        items.append(("sensor", f"{DEVICE_ID}_state_super",
                      sensor("sensor", "state_super", f"{DEVICE_NAME} State Super",
                             f"{BASE_TOPIC}/status", "{{ value_json.state_super|int }}",
                             None, None, "mdi:fire")))

    # operating: boiler_ref (Ist des Targets)
    if "boiler_ref" not in EXCLUDE_SET:
        items.append(("sensor", f"{DEVICE_ID}_boiler_ref",
                      sensor("sensor", "boiler_ref", f"{DEVICE_NAME} Boiler Ref",
                             f"{BASE_TOPIC}/operating", "{{ value_json.boiler_ref|float }}",
                             "°C", "temperature", None, "measurement")))

    # settings/regulation: operation_mode, fixed_power
    if "operation_mode" not in EXCLUDE_SET:
        items.append(("sensor", f"{DEVICE_ID}_operation_mode",
                      sensor("sensor", "operation_mode", f"{DEVICE_NAME} Operation Mode",
                             f"{BASE_TOPIC}/settings/regulation", "{{ value_json.operation_mode|int }}")))

    if "fixed_power" not in EXCLUDE_SET:
        items.append(("sensor", f"{DEVICE_ID}_fixed_power",
                      sensor("sensor", "fixed_power", f"{DEVICE_NAME} Fixed Power",
                             f"{BASE_TOPIC}/settings/regulation", "{{ value_json.fixed_power|int }}",
                             "%")))

    return items

def main():
    c = mqtt_connect()
    c.loop_start()

    # Climate
    publish_config(c, disc_topic("climate"), build_climate_payload())

    # Force Auger
    publish_config(c, disc_topic("number", f"{DEVICE_ID}_force_auger"), build_force_auger_payload())

    # Sensors
    for kind, object_id, payload in build_sensors():
        publish_config(c, disc_topic(kind, object_id), payload)

    time.sleep(0.3)
    c.loop_stop()
    c.disconnect()
    print("[discovery] climate, number, sensors published.")

if __name__ == "__main__":
    main()
