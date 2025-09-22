#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Home Assistant MQTT Discovery for Aduro2MQTT

- Climate (modes: off/heat/auto)
  - off  -> send {"path":"misc.stop","value":"1"}
  - heat -> send {"path":"misc.start","value":"1"}  and {"path":"regulation.operation_mode","value":0}
  - auto -> send {"path":"misc.start","value":"1"}  and {"path":"regulation.operation_mode","value":1}
  - current temp  : status.boiler_temp  (Raumtemperatur)
  - target temp   : settings/boiler.temp  (Raum-Soll)
- Select fixed_power (10/50/100)
- Number force_auger
- Button ignite (Zündung)
- A few essential sensors

Environment (vom Add-on gesetzt):
  DISCOVERY_PREFIX (default "homeassistant")
  BASE_TOPIC       (default "aduro2mqtt")
  DEVICE_NAME      (default "Aduro H2")
  DEVICE_ID        (default "aduro_h2")
  MQTT_HOST        (default "core-mosquitto")
  MQTT_PORT        (default 1883)
  MQTT_USER / MQTT_USERNAME (optional)
  MQTT_PASSWORD    (optional)
  DISCOVERY_EXCLUDE (comma separated, case-insensitive)
"""

import json
import os
import time
import paho.mqtt.client as mqtt

# ---- ENV / Defaults ----
DISCOVERY_PREFIX = os.getenv("DISCOVERY_PREFIX", "homeassistant").strip()
BASE_TOPIC       = os.getenv("BASE_TOPIC", "aduro2mqtt").strip()
DEVICE_NAME      = os.getenv("DEVICE_NAME", "Aduro H2").strip()
DEVICE_ID        = os.getenv("DEVICE_ID", "aduro_h2").strip()

MQTT_HOST        = os.getenv("MQTT_HOST", "core-mosquitto").strip()
MQTT_PORT        = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER        = os.getenv("MQTT_USER") or os.getenv("MQTT_USERNAME")
MQTT_PASSWORD    = os.getenv("MQTT_PASSWORD", "")

EXCLUDE_RAW      = os.getenv("DISCOVERY_EXCLUDE", "boiler_pump_state,return_temp")
EXCLUDE          = set(e.strip().lower() for e in EXCLUDE_RAW.split(",") if e.strip())

# ---- Helpers ----
def client_connect() -> mqtt.Client:
    c = mqtt.Client(client_id=f"{DEVICE_ID}_disc")
    if MQTT_USER:
        c.username_pw_set(MQTT_USER, MQTT_PASSWORD or "")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    return c

def disc_topic(kind: str, object_id: str) -> str:
    return f"{DISCOVERY_PREFIX}/{kind}/{DEVICE_ID}_{object_id}/config"

def device_payload_full():
    return {
        "identifiers": [DEVICE_ID],
        "name": DEVICE_NAME,
        "manufacturer": "Aduro",
        "model": "via aduro2mqtt",
    }

def device_payload_short():
    return {"ids": [DEVICE_ID], "name": DEVICE_NAME, "mf": "Aduro", "mdl": "via aduro2mqtt"}

def publish_entity_short(client, kind, object_id, payload: dict):
    topic = disc_topic(kind, object_id)
    payload = dict(payload)  # copy
    payload["uniq_id"] = f"{DEVICE_ID}_{object_id}"
    payload["dev"] = device_payload_short()
    client.publish(topic, json.dumps(payload, ensure_ascii=False, separators=(",", ":")), qos=1, retain=True)

def publish_climate(client):
    """
    HVAC modes:
      - 'off'  -> misc.stop
      - 'heat' -> misc.start + operation_mode=0 (Fixed Power)
      - 'auto' -> misc.start + operation_mode=1 (Temperature regulation)
    mode_state_template nutzt STATUS (für An/Aus) + operation_mode (aus STATUS),
    weil im Status JSON die Keys 'state', 'substate' und 'operation_mode' vorkommen.
    """
    topic = f"{DISCOVERY_PREFIX}/climate/{DEVICE_ID}_climate/config"

    mode_cmd_tpl = (
        "{% if value == 'off' %}"
        "{\"path\":\"misc.stop\",\"value\":\"1\"}"
        "{% elif value == 'auto' %}"
        "{\"path\":\"regulation.operation_mode\",\"value\":1}"
        "{% else %}"
        "{\"path\":\"regulation.operation_mode\",\"value\":0}"
        "{% endif %}"
    )

    # Wir senden *immer* auch Start, wenn nicht 'off' (damit der Ofen läuft)
    mode_cmd_t = f"{BASE_TOPIC}/set"
    mode_cmd_wrap = (
        "{% if value == 'off' %}"
        + mode_cmd_tpl +
        "{% else %}"
        "{\"multi\":["
        + mode_cmd_tpl +
        ", {\"path\":\"misc.start\",\"value\":\"1\"}"
        "]}"
        "{% endif %}"
    )

    mode_state_tpl = """
    {% set s  = (value_json.state|int) if ('state' in value_json) else 14 %}
    {% set ss = (value_json.substate|int) if ('substate' in value_json) else 0 %}
    {% if s == 14 and ss in [0,6] %}
      off
    {% else %}
      {% if (value_json.operation_mode|int) == 1 %}
        auto
      {% else %}
        heat
      {% endif %}
    {% endif %}
    """

    payload = {
        "name": DEVICE_NAME,
        "unique_id": f"{DEVICE_ID}_climate",
        "device": device_payload_full(),

        # HVAC modes & mapping
        "modes": ["off", "heat", "auto"],
        "mode_command_topic": mode_cmd_t,
        "mode_command_template": mode_cmd_wrap,
        "mode_state_topic": f"{BASE_TOPIC}/status",
        "mode_state_template": mode_state_tpl,

        # Target temperature -> settings/boiler.temp
        "temperature_command_topic": f"{BASE_TOPIC}/set",
        "temperature_command_template": "{\"path\":\"boiler.temp\",\"value\": {{ value|float }} }",
        "temperature_state_topic": f"{BASE_TOPIC}/settings/boiler",
        "temperature_state_template": "{{ value_json.temp|float if value_json.temp is defined else value_json['temp']|float }}",

        # Current temperature -> status.boiler_temp (= Raumtemperatur)
        "current_temperature_topic": f"{BASE_TOPIC}/status",
        "current_temperature_template": "{{ (value_json.boiler_temp|float) if (value_json.boiler_temp is defined) else (value_json.room_temp|float) }}",

        "temperature_unit": "C",
        "min_temp": 5,
        "max_temp": 35,
        "temp_step": 1,
    }

    client.publish(topic, json.dumps(payload, ensure_ascii=False, separators=(",", ":")), qos=1, retain=True)
    print(f"[discovery] published climate -> {topic}")

def publish_select_fixed_power(client):
    payload = {
        "name": f"{DEVICE_NAME} Fixed power (%)",
        "cmd_t": f"{BASE_TOPIC}/set",
        "cmd_tpl": "{\"path\":\"regulation.fixed_power\",\"value\": {{ value|int }} }",
        "stat_t": f"{BASE_TOPIC}/settings/regulation",
        "val_tpl": "{{ value_json.fixed_power | int }}",
        "options": ["10", "50", "100"],
        "icon": "mdi:percent",
    }
    publish_entity_short(client, "select", "fixed_power", payload)

def publish_number_force_auger(client):
    payload = {
        "name": f"{DEVICE_NAME} Force Auger (s)",
        "cmd_t": f"{BASE_TOPIC}/set",
        "cmd_tpl": "{\"path\":\"auger.forced_run\",\"value\": {{ value|int }} }",
        "stat_t": f"{BASE_TOPIC}/settings/auger",
        "val_tpl": "{{ value_json.forced_run|int if value_json.forced_run is defined else 0 }}",
        "min": 0, "max": 120, "step": 5,
        "mode": "slider",
        "icon": "mdi:rotate-right",
    }
    publish_entity_short(client, "number", "force_auger", payload)

def publish_button_ignite(client):
    payload = {
        "name": f"{DEVICE_NAME} Zündung",
        "cmd_t": f"{BASE_TOPIC}/set",
        "cmd_tpl": "{\"path\":\"misc.start\",\"value\":\"1\"}",
        "icon": "mdi:fire",
    }
    publish_entity_short(client, "button", "ignite", payload)

def publish_sensors(client):
    sensors = {
        # Anzeigename, Topic, Value-Template, Einheit, device_class, state_class
        "room_temp": (
            f"{DEVICE_NAME} Room Temp",
            f"{BASE_TOPIC}/status",
            "{{ value_json.boiler_temp|float }}",
            "°C", "temperature", "measurement",
        ),
        "smoke_temp": (
            f"{DEVICE_NAME} Smoke Temp",
            f"{BASE_TOPIC}/status",
            "{{ value_json.smoke_temp|float }}",
            "°C", "temperature", "measurement",
        ),
        "power_pct": (
            f"{DEVICE_NAME} Power",
            f"{BASE_TOPIC}/status",
            "{{ value_json.power_pct|float }}",
            "%", None, "measurement",
        ),
        "state_txt": (
            f"{DEVICE_NAME} State",
            f"{BASE_TOPIC}/status",
            """
            {% set s = value_json.state|int %}
            {% set ss = value_json.substate|int %}
            {% if s == 14 %}
              {% if ss == 0 %}Aus
              {% elif ss == 6 %}Aus eingeleitet
              {% else %}Unbekannt (14/{{ ss }})
              {% endif %}
            {% elif s == 2 %}Zündung eingeleitet
            {% elif s == 4 %}Zündung verlängert
            {% elif s == 32 %}Betrieb, Aufheizen
            {% elif s == 5 %}Betrieb, Normal
            {% elif s == 0 %}Betrieb, Warten
            {% else %}Unbekannt ({{ s }})
            {% endif %}
            """,
            None, None, None,
        ),
        "co_sensor": (
            f"{DEVICE_NAME} CO",
            f"{BASE_TOPIC}/status",
            "{{ value_json['drift.co'] | default(value_json.co, true) | int }}",
            None, None, "measurement",
        ),
    }

    for key, (name, stat_t, val_tpl, unit, dev_cla, stat_cla) in sensors.items():
        if key.lower() in EXCLUDE:
            continue
        payload = {"name": name, "stat_t": stat_t, "val_tpl": val_tpl}
        if unit:     payload["unit_of_meas"] = unit
        if dev_cla:  payload["dev_cla"] = dev_cla
        if stat_cla: payload["stat_cla"] = stat_cla
        publish_entity_short(client, "sensor", key, payload)

def main():
    print(f"[discovery] mqtt={MQTT_HOST}:{MQTT_PORT} user={'<set>' if MQTT_USER else '<none>'}")
    print(f"[discovery] prefix={DISCOVERY_PREFIX} device={DEVICE_NAME}/{DEVICE_ID} base={BASE_TOPIC}")
    print(f"[discovery] exclude={sorted(EXCLUDE)}")

    client = client_connect()

    # Publish all discovery entities
    publish_climate(client)
    publish_select_fixed_power(client)
    publish_number_force_auger(client)
    publish_button_ignite(client)
    publish_sensors(client)

    # Flush and disconnect
    client.loop_start()
    time.sleep(0.5)
    client.loop_stop()
    client.disconnect()
    print("[discovery] done")

if __name__ == "__main__":
    main()
