#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os, time
import paho.mqtt.client as mqtt

# ---- ENV aus run.sh / Add-on-Optionen ----
DISCOVERY_PREFIX = os.getenv("DISCOVERY_PREFIX", "homeassistant").strip()
BASE_TOPIC       = os.getenv("BASE_TOPIC", "aduro2mqtt").strip()
DEVICE_NAME      = os.getenv("DEVICE_NAME", "Aduro H2").strip()
DEVICE_ID        = os.getenv("DEVICE_ID", "aduro_h2").strip()

MQTT_HOST        = os.getenv("MQTT_HOST", "core-mosquitto").strip()
MQTT_PORT        = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER        = os.getenv("MQTT_USER")
MQTT_PASSWORD    = os.getenv("MQTT_PASSWORD")

# Exclude-Liste wie in deinem run.sh default
EXCLUDE_RAW      = os.getenv("DISCOVERY_EXCLUDE", "boiler_pump_state,return_temp")
EXCLUDE          = set(e.strip().lower() for e in EXCLUDE_RAW.split(",") if e.strip())

TEMP_MODE_VALUE  = 1  # Aduro H2: Temperaturregelung

def client_connect() -> mqtt.Client:
    c = mqtt.Client(client_id=f"{DEVICE_ID}_disc")
    if MQTT_USER:
        c.username_pw_set(MQTT_USER, MQTT_PASSWORD or "")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    return c

def disc_topic(kind: str, object_id: str) -> str:
    # Einheitliche Object-IDs: <DEVICE_ID>_<object>
    return f"{DISCOVERY_PREFIX}/{kind}/{DEVICE_ID}_{object_id}/config"

def device_payload():
    # Kurze Keys wie in deiner Altversion (HA versteht die Kurzformen)
    return {"ids": [DEVICE_ID], "name": DEVICE_NAME, "mf": "Aduro", "mdl": "via aduro2mqtt"}

def publish_entity(client, kind, object_id, payload):
    full = disc_topic(kind, object_id)
    payload["uniq_id"] = f"{DEVICE_ID}_{object_id}"
    payload["dev"] = device_payload()
    # kompakte JSON-Ausgabe
    client.publish(full, json.dumps(payload, ensure_ascii=False, separators=(",", ":")), retain=True)

def publish_climate(client):
    # Climate mit Presets (Temperature / Power 10/50/100)
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

    payload = {
        "name": DEVICE_NAME,
        # HVAC an/aus
        "modes": ["off","heat"],
        "mode_command_topic": f"{BASE_TOPIC}/set",
        "mode_command_template": (
            "{% if value == 'off' %}{\"path\":\"misc.stop\",\"value\":\"1\"}"
            "{% else %}{\"path\":\"misc.start\",\"value\":\"1\"}{% endif %}"
        ),
        "mode_state_topic": f"{BASE_TOPIC}/status",
        "mode_state_template": "{{ 'heat' if (value_json.state_super|int) == 1 else 'off' }}",

        # Presets für Temperatur-/Powerbetrieb
        "preset_modes": ["Temperature","Power 10","Power 50","Power 100"],
        "preset_mode_command_topic": f"{BASE_TOPIC}/set",
        "preset_mode_command_template": preset_cmd,
        "preset_mode_state_topic": f"{BASE_TOPIC}/settings/regulation",
        "preset_mode_state_template": preset_state,

        # Target-Temp: Kommando auf boiler.ref, State aus settings/boiler.ref (verhindert 25°C-Rücksprung)
        "temperature_command_topic": f"{BASE_TOPIC}/set",
        "temperature_command_template": "{\"path\":\"boiler.ref\",\"value\": {{ value|float }} }",
        "temperature_state_topic": f"{BASE_TOPIC}/settings/boiler",
        "temperature_state_template": "{{ value_json.ref|float }}",

        # Ist-Temp: room_temp mit Fallback auf boiler_temp
        "current_temperature_topic": f"{BASE_TOPIC}/status",
        "current_temperature_template": "{{ (value_json.room_temp | default(value_json.boiler_temp)) | float }}",

        "temperature_unit": "C",
        "min_temp": 10,
        "max_temp": 30,
        "temp_step": 0.5
    }
    # Climate bekommt ein klareres Objekt: <device>_climate
    publish_entity(client, "climate", "climate", payload)

def publish_switch(client):
    # Heizbetrieb EIN/AUS als Switch
    payload = {
        "name": f"{DEVICE_NAME} Heating",
        "cmd_t": f"{BASE_TOPIC}/set",
        "cmd_tpl": (
            "{% if value in ['ON','on','true','True',1] %}"
            "{\"path\":\"misc.start\",\"value\":\"1\"}"
            "{% else %}"
            "{\"path\":\"misc.stop\",\"value\":\"1\"}"
            "{% endif %}"
        ),
        "stat_t": f"{BASE_TOPIC}/status",
        "val_tpl": "{{ 'ON' if (value_json.state_super|int) == 1 else 'OFF' }}",
        "icon": "mdi:radiator",
        "opt": True
    }
    publish_entity(client, "switch", "heating", payload)

def publish_number_force_auger(client):
    payload = {
        "name": f"{DEVICE_NAME} Force Auger (s)",
        "cmd_t": f"{BASE_TOPIC}/set",
        "cmd_tpl": "{\"path\":\"auger.forced_run\",\"value\": {{ value|int }} }",
        "stat_t": f"{BASE_TOPIC}/settings/auger",
        "val_tpl": "{{ value_json.forced_run|int if value_json.forced_run is defined else 0 }}",
        "min": 0, "max": 120, "step": 5,
        "mode": "slider"
    }
    publish_entity(client, "number", "force_auger", payload)

def publish_sensors(client):
    # Sensoren wie in deiner Altversion – inkl. Room Temp aus boiler_temp
    sensors = {
        "room_temp":        (f"{DEVICE_NAME} Room Temperature",   f"{BASE_TOPIC}/status",              "{{ value_json.boiler_temp|float }}", "°C", "temperature", "measurement"),
        "boiler_temp":      (f"{DEVICE_NAME} Boiler Temperature", f"{BASE_TOPIC}/status",              "{{ value_json.boiler_temp|float }}", "°C", "temperature", "measurement"),
        "state_super":      (f"{DEVICE_NAME} State Super",        f"{BASE_TOPIC}/status",              "{{ value_json.state_super|int }}",   None, None, None),
        "boiler_ref":       (f"{DEVICE_NAME} Boiler Ref",         f"{BASE_TOPIC}/settings/boiler",     "{{ value_json.ref|float }}",         "°C", "temperature", "measurement"),
        "operation_mode":   (f"{DEVICE_NAME} Operation Mode",     f"{BASE_TOPIC}/settings/regulation", "{{ value_json.operation_mode|int }}", None, None, None),
        "fixed_power":      (f"{DEVICE_NAME} Fixed Power",        f"{BASE_TOPIC}/settings/regulation", "{{ value_json.fixed_power|int }}",   "%",  None, "measurement"),
        # optional abwählbar wie früher:
        "boiler_pump_state":(f"{DEVICE_NAME} Boiler Pump",        f"{BASE_TOPIC}/operating",           "{{ value_json.boiler_pump_state|int }}", "", None, None),
        "return_temp":      (f"{DEVICE_NAME} Return Temp",        f"{BASE_TOPIC}/operating",           "{{ value_json.return_temp|float }}", "°C", "temperature", "measurement"),
    }

    for key, (name, stat_t, val_tpl, unit, dev_cla, stat_cla) in sensors.items():
        if key.lower() in EXCLUDE:
            continue
        payload = {"name": name, "stat_t": stat_t, "val_tpl": val_tpl}
        if unit:     payload["unit_of_meas"] = unit
        if dev_cla:  payload["dev_cla"] = dev_cla
        if stat_cla: payload["stat_cla"] = stat_cla
        publish_entity(client, "sensor", key, payload)

def main():
    print(f"[discovery] connect mqtt host={MQTT_HOST} port={MQTT_PORT} user={'<set>' if MQTT_USER else '<none>'}")
    print(f"[discovery] discovery_prefix={DISCOVERY_PREFIX} device={DEVICE_NAME}/{DEVICE_ID} base={BASE_TOPIC}")
    print(f"[discovery] exclude={sorted(EXCLUDE)}")

    client = client_connect()

    # Entities publishen (retain)
    publish_climate(client)
    publish_switch(client)
    publish_number_force_auger(client)
    publish_sensors(client)

    client.loop_start()
    time.sleep(0.5)
    client.loop_stop()
    client.disconnect()
    print("[discovery] done")

if __name__ == "__main__":
    main()
