#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aduro2mqttAddon MQTT Discovery

- climate (hvac_modes: off/heat)
  * preset_modes: Temperature, Power 10, Power 50, Power 100
    -> Temperature: regulation.operation_mode = 1
    -> Power X:    regulation.fixed_power   = X
  * target temperature: boiler.ref  (state from settings/boiler.ref)
  * current temperature: room_temp (fallback boiler_temp)

- number: Force Auger (s)
"""

import os, json, time
from typing import Dict, Any
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

TEMP_MODE_VALUE  = 1  # Aduro H2: Temperaturregelung = 1

DEVICE = {
    "identifiers": [DEVICE_ID],
    "name": DEVICE_NAME,
    "manufacturer": "Aduro",
    "model": "via aduro2mqtt",
}

def disc_topic(kind: str, object_id: str = "") -> str:
    """Discovery-Topic nach HA-Schema."""
    if object_id:
        return f"{DISCOVERY_PREFIX}/{kind}/{object_id}/config"
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

def build_climate_payload() -> Dict[str, Any]:
    # Preset -> Command
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
    # Preset-State aus settings/regulation ableiten
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

        # Presets (ersetzt separaten Fixed-Power-Select)
        "preset_modes": ["Temperature","Power 10","Power 50","Power 100"],
        "preset_mode_command_topic": f"{BASE_TOPIC}/set",
        "preset_mode_command_template": preset_cmd,
        "preset_mode_state_topic": f"{BASE_TOPIC}/settings/regulation",
        "preset_mode_state_template": preset_state,

        # Zieltemperatur (Command -> boiler.ref; State direkt aus settings/boiler.ref)
        "temperature_command_topic": f"{BASE_TOPIC}/set",
        "temperature_command_template": "{\"path\":\"boiler.ref\",\"value\": {{ value|float }} }",
        "temperature_state_topic": f"{BASE_TOPIC}/settings/boiler",
        "temperature_state_template": "{{ value_json.ref|float }}",

        # Ist-Temperatur
        "current_temperature_topic": f"{BASE_TOPIC}/status",
        "current_temperature_template": "{{ (value_json.room_temp | default(value_json.boiler_temp)) | float }}",

        "temperature_unit": "C",
        "min_temp": 10,
        "max_temp": 30,
        "temp_step": 0.5,
    }

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

def main():
    c = mqtt_connect()
    c.loop_start()

    # Climate mit Presets
    publish_config(c, disc_topic("climate"), build_climate_payload())

    # Force Auger (praktisch, unabhängig vom Preset)
    publish_config(c, disc_topic("number", f"{DEVICE_ID}_force_auger"), build_force_auger_payload())

    time.sleep(0.3)
    c.loop_stop()
    c.disconnect()
    print("[discovery] climate+force_auger published.")

if __name__ == "__main__":
    main()
