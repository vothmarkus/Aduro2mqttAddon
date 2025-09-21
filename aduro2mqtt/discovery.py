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
MQTT_USER        = os.getenv("MQTT_USER") or os.getenv("MQTT_USERNAME")
MQTT_PASSWORD    = os.getenv("MQTT_PASSWORD", "")

# Für Basic-Climate
DEVICE_PREFIX    = BASE_TOPIC

# optionales Exclude (wie in run.sh)
EXCLUDE_RAW      = os.getenv("DISCOVERY_EXCLUDE", "boiler_pump_state,return_temp")
EXCLUDE          = set(e.strip().lower() for e in EXCLUDE_RAW.split(",") if e.strip())

def client_connect() -> mqtt.Client:
    c = mqtt.Client(client_id=f"{DEVICE_ID}_disc")
    if MQTT_USER:
        c.username_pw_set(MQTT_USER, MQTT_PASSWORD or "")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    return c

def disc_topic(kind: str, object_id: str) -> str:
    return f"{DISCOVERY_PREFIX}/{kind}/{DEVICE_ID}_{object_id}/config"

def device_payload_full():
    return {"identifiers":[DEVICE_ID],"name":DEVICE_NAME,"manufacturer":"Aduro","model":"via aduro2mqtt"}

def device_payload_short():
    return {"ids":[DEVICE_ID],"name":DEVICE_NAME,"mf":"Aduro","mdl":"via aduro2mqtt"}

def publish_entity_short(client, kind, object_id, payload):
    full = disc_topic(kind, object_id)
    payload["uniq_id"] = f"{DEVICE_ID}_{object_id}"
    payload["dev"] = device_payload_short()
    client.publish(full, json.dumps(payload, ensure_ascii=False, separators=(",",":")), qos=1, retain=True)

def publish_entity_full(client, payload):
    full = f"{DISCOVERY_PREFIX}/climate/{DEVICE_ID}/config"
    payload["uniq_id"] = f"{DEVICE_ID}_climate"
    payload["device"] = device_payload_full()
    client.publish(full, json.dumps(payload, ensure_ascii=False, separators=(",",":")), qos=1, retain=True)

# ---------- CLIMATE ----------
def publish_entity_full(client, payload):
    # Climate bewusst unter .../climate/aduro_h2_climate/config veröffentlichen
    full = f"{DISCOVERY_PREFIX}/climate/{DEVICE_ID}_climate/config"
    payload["uniq_id"] = f"{DEVICE_ID}_climate"
    payload["device"] = {
        "identifiers": [DEVICE_ID],
        "name": DEVICE_NAME,
        "manufacturer": "Aduro",
        "model": "via aduro2mqtt",
    }
    client.publish(full, json.dumps(payload, ensure_ascii=False, separators=(",",":")), qos=1, retain=True)
    print(f"[discovery] published climate -> {full}")

def publish_entity_full(client, payload):
    # Climate bewusst unter .../climate/<DEVICE_ID>_climate/config veröffentlichen
    disc = f"{DISCOVERY_PREFIX}/climate/{DEVICE_ID}_climate/config"
    # volle Device-Infos
    device_full = {
        "identifiers": [DEVICE_ID],
        "name": DEVICE_NAME,
        "manufacturer": "Aduro",
        "model": "via aduro2mqtt",
    }
    # IDs doppelt setzen (kompatibel zu allen HA-Versionen)
    payload["unique_id"] = f"{DEVICE_ID}_climate"
    payload["uniq_id"]   = f"{DEVICE_ID}_climate"
    payload["device"]    = device_full
    client.publish(disc, json.dumps(payload, ensure_ascii=False, separators=(",",":")), qos=1, retain=True)
    print(f"[discovery] published climate -> {disc}")

def publish_climate(client):
    # Preset-Commands (Temperaturregelung vs. feste Leistung)
    preset_cmd = (
        "{% if value == 'Temperature' %}"
        "{{\"path\":\"regulation.operation_mode\",\"value\":1}}"
        "{% elif value == '10' %}"
        "{{\"path\":\"regulation.fixed_power\",\"value\":10}}"
        "{% elif value == '50' %}"
        "{{\"path\":\"regulation.fixed_power\",\"value\":50}}"
        "{% elif value == '100' %}"
        "{{\"path\":\"regulation.fixed_power\",\"value\":100}}"
        "{% endif %}"
    )
    # Aus STATUS lesen; Punkt-Keys via Index!
    preset_tpl = (
        "{{ 'Temperature' if (value_json.operation_mode|int) == 1 "
        "else ((value_json['regulation.fixed_power']|int) ~ '') }}"
    )

    payload = {
        "name": DEVICE_NAME,

        # nur gültige HVAC-Modi (sonst verwirft HA die Entity)
        "modes": ["off", "heat"],
        "mode_command_topic": f"{DEVICE_PREFIX}/set",
        "mode_command_template":
            "{% if value == 'off' %}{\"path\":\"misc.stop\",\"value\":\"1\"}"
            "{% else %}{\"path\":\"misc.start\",\"value\":\"1\"}{% endif %}",
        "mode_state_topic": f"{DEVICE_PREFIX}/status",
        "mode_state_template": "{{ 'heat' if (value_json.state_super|int) == 1 else 'off' }}",

        # ---- Presets (DOKU-konform) ----
        "preset_modes": ["Temperature", "10", "50", "100"],
        "preset_mode_command_topic": f"{DEVICE_PREFIX}/set",
        "preset_mode_command_template": preset_cmd,
        "preset_mode_state_topic": f"{DEVICE_PREFIX}/status",
        "preset_mode_value_template": preset_tpl,

        # Zieltemperatur (bewährter Pfad)
        "temperature_command_topic": f"{DEVICE_PREFIX}/set",
        "temperature_command_template": "{\"path\":\"boiler.ref\",\"value\": {{ value|float }} }",
        "temperature_state_topic": f"{DEVICE_PREFIX}/operating",
        "temperature_state_template": "{{ value_json.boiler_ref|float }}",

        # Ist-Temperatur
        "current_temperature_topic": f"{DEVICE_PREFIX}/status",
        "current_temperature_template": "{{ (value_json.room_temp | default(value_json.boiler_temp)) | float }}",

        # Limits/Step wie gewünscht
        "temperature_unit": "C",
        "min_temp": 5,
        "max_temp": 35,
        "temp_step": 1
    }
    publish_entity_full(client, payload)

# ---------- SWITCH (Heizbetrieb) ----------
def publish_switch(client):
    payload = {
        "name": f"{DEVICE_NAME} Heating",
        "cmd_t": f"{BASE_TOPIC}/set",
        "cmd_tpl":
            "{% if value in ['ON','on','true','True',1] %}"
            "{\"path\":\"misc.start\",\"value\":\"1\"}"
            "{% else %}"
            "{\"path\":\"misc.stop\",\"value\":\"1\"}"
            "{% endif %}",
        "stat_t": f"{BASE_TOPIC}/status",
        "val_tpl": "{{ 'ON' if (value_json.state_super|int) == 1 else 'OFF' }}",
        "icon": "mdi:radiator",
        "opt": True
    }
    publish_entity_short(client, "switch", "heating", payload)

# ---------- SWITCH (fixed_power) ----------
def publish_fixed_power(client):
    payload = {
        "name": f"{DEVICE_NAME} Fixed power (%)",
        "cmd_t": f"{BASE_TOPIC}/set",
        "cmd_tpl": '{"path": "regulation.fixed_power", "value": {{ value }} }',
        "stat_t": f"{BASE_TOPIC}/settings/regulation",
        "val_tpl": "{{ value_json.fixed_power | int }}",
        "options": ["10","50","100"],
    }
    publish_entity_short(client, "select", "fixed_power", payload)

# ---------- NUMBER (Force Auger) ----------
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
    publish_entity_short(client, "number", "force_auger", payload)

# ---------- SENSORS (ohne boiler_temp & outdoor_temp) ----------
def publish_sensors(client):
    sensors = {
        # „Room Temp“ robust aus boiler_temp (nur Anzeigezweck)
        "room_temp":   (f"{DEVICE_NAME} Room Temp", f"{BASE_TOPIC}/status", "{{ value_json.boiler_temp|float }}", "°C", "temperature", "measurement"),
        "smoke_temp":  (f"{DEVICE_NAME} Smoke Temp",  f"{BASE_TOPIC}/status", "{{ value_json.smoke_temp|float }}", "°C", "temperature", "measurement"),
        "state":       (f"{DEVICE_NAME} State",       f"{BASE_TOPIC}/status", "{{ value_json.state|int }}",       None, None, None),
        "state_sec":   (f"{DEVICE_NAME} State Sec",   f"{BASE_TOPIC}/status", "{{ value_json.state_sec|int }}",   "s",  None, "measurement"),
        "state_super": (f"{DEVICE_NAME} State Super", f"{BASE_TOPIC}/status", "{{ value_json.state_super|int }}", None, None, None),
        "substate":    (f"{DEVICE_NAME} Substate",    f"{BASE_TOPIC}/status", "{{ value_json.substate|int }}",    None, None, None),
        "substate_sec":(f"{DEVICE_NAME} Substate Sec",f"{BASE_TOPIC}/status", "{{ value_json.substate_sec|int }}","s",  None, "measurement"),
        "operation_mode": (f"{DEVICE_NAME} Operation Mode", f"{BASE_TOPIC}/status", "{{ value_json.operation_mode|int }}", None, None, None),
        "oxygen":      (f"{DEVICE_NAME} Oxygen",      f"{BASE_TOPIC}/status", "{{ value_json.oxygen|float }}", "%", None, "measurement"),
        "power_pct":   (f"{DEVICE_NAME} Power Pct",   f"{BASE_TOPIC}/status", "{{ value_json.power_pct|float }}", "%", None, "measurement"),
        "exhaust_speed": (f"{DEVICE_NAME} Exhaust Speed", f"{BASE_TOPIC}/status", "{{ value_json.exhaust_speed|float }}", "", None, "measurement"),

        # optional via EXCLUDE:
        "boiler_pump_state": (f"{DEVICE_NAME} Boiler Pump", f"{BASE_TOPIC}/operating", "{{ value_json.boiler_pump_state|int }}", "", None, None),
        "return_temp":       (f"{DEVICE_NAME} Return Temp", f"{BASE_TOPIC}/operating", "{{ value_json.return_temp|float }}", "°C", "temperature", "measurement"),
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

    publish_climate(client)
    publish_switch(client)
    publish_fixed_power(client)
    publish_number_force_auger(client)
    publish_sensors(client)

    client.loop_start()
    time.sleep(0.5)
    client.loop_stop()
    client.disconnect()
    print("[discovery] done")

if __name__ == "__main__":
    main()
