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
    # HVAC mode -> operation_mode (auto=1, heat=0)
    mode_cmd_tpl = """
      {% if value == 'auto' %}
        {"path":"regulation.operation_mode","value":1}
      {% else %}
        {"path":"regulation.operation_mode","value":0}
      {% endif %}
    """

    # operation_mode -> HVAC mode
    mode_state_tpl = (
        "{{ 'auto' if (value_json.operation_mode|int) == 1 else 'heat' }}"
    )

    payload = {
        "name": DEVICE_NAME,
        "modes": ["auto", "heat"],

        # Mode steuern/lesen über settings.regulation.operation_mode
        "mode_command_topic": f"{DEVICE_PREFIX}/set",
        "mode_command_template": mode_cmd_tpl,
        "mode_state_topic": f"{DEVICE_PREFIX}/settings/regulation",
        "mode_state_template": mode_state_tpl,
        
        
        # ---- Presets (nur im Fixmodus relevant) ----
#         "preset_modes": ["eco", "comfort", "boost"],
#         "preset_mode_command_topic": f"{DEVICE_PREFIX}/set",
#         "preset_mode_command_template": """
#           {% if value == 'eco' %}
#             {"path":"regulation.fixed_power","value":10}
#           {% elif value == 'comfort' %}
#             {"path":"regulation.fixed_power","value":50}
#           {% elif value == 'boost' %}
#             {"path":"regulation.fixed_power","value":100}
#           {% endif %}
#         """,
#         "preset_mode_state_topic": f"{DEVICE_PREFIX}/status",
#         "preset_mode_value_template": """
#           {% if (value_json['regulation.fixed_power']|int) == 10 %}
#             eco
#           {% elif (value_json['regulation.fixed_power']|int) == 50 %}
#             comfort
#           {% elif (value_json['regulation.fixed_power']|int) == 100 %}
#             boost
#           {% else %}
#             none
#           {% endif %}
#         """,
        

        # Solltemperatur setzen -> boiler.temp (SETTINGS)
        "temperature_command_topic": f"{DEVICE_PREFIX}/set",
        "temperature_command_template": "{\"path\":\"boiler.temp\",\"value\": {{ value|float }} }",

        # Solltemperatur-STATE aus settings boiler
        "temperature_state_topic": f"{DEVICE_PREFIX}/settings/boiler",
        "temperature_state_template": "{{ value_json.temp | float }}",

        # Ist-Temperatur: bevorzugt room_temp, sonst boiler_temp
        "current_temperature_topic": f"{DEVICE_PREFIX}/status",
        "current_temperature_template": "{{ (value_json.room_temp | default(value_json.boiler_temp)) | float }}",

        "temperature_unit": "C",
        "min_temp": 5,
        "max_temp": 35,
        "temp_step": 1,

        "unique_id": f"{DEVICE_ID}_climate",
        "device": {
            "identifiers": [DEVICE_ID],
            "name": DEVICE_NAME,
            "manufacturer": "Aduro",
            "model": "via aduro2mqtt"
        }
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
        "val_tpl": """
            {% set s = value_json.state|int %}
            {% set ss = value_json.substate|int %}
            {% if s == 14 and ss in [0,6] %}
              OFF
            {% else %}
              ON
            {% endif %}
        """,
        "icon": "mdi:radiator",
        "opt": False   # nicht optimistisch, nur echte Rückmeldung zählt
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
        "name": f"{DEVICE_NAME} Force Auger (in s)",
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
        "room_temp":   (f"{DEVICE_NAME} Room Temp", f"{BASE_TOPIC}/status", "{{ value_json.boiler_temp|float }}", "°C", "temperature", "measurement"),
        "smoke_temp":  (f"{DEVICE_NAME} Smoke Temp", f"{BASE_TOPIC}/status", "{{ value_json.smoke_temp|float }}", "°C", "temperature", "measurement"),
        # neuer Text-Sensor für State
        "state_txt":   (
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
            {% elif s == 6 %}Betrieb, Temperatur erreicht
            {% elif s == 9 %}Angehalten, Holzverbrennung
            {% elif s == 20 %}Angehalten, Flamme erloschen
            {% elif s == 13 %}Angehalten, Zündung fehlgeschlagen
            {% elif s == 28 %}28???
            {% else %}Unbekannt ({{ s }})
            {% endif %}
            """,
            None, None, None
        ),
        "state":       (f"{DEVICE_NAME} State Nr",       f"{BASE_TOPIC}/status", "{{ value_json.state|int }}",    None, None, None),
        "substate":    (f"{DEVICE_NAME} Substate Nr",    f"{BASE_TOPIC}/status", "{{ value_json.substate|int }}", None, None, None),
        "state_sec":   (f"{DEVICE_NAME} State Time",   f"{BASE_TOPIC}/status", "{{ value_json.state_sec|int }}","s", None, "measurement"),
        "power_pct":   (f"{DEVICE_NAME} Power Pct",   f"{BASE_TOPIC}/status", "{{ value_json.power_pct|float }}","%", None, "measurement"),
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
