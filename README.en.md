# Aduro2MQTT – Home Assistant Add-on

Bridges your **Aduro H2** (and compatible Aduro boilers) to **MQTT** and auto-creates key entities in Home Assistant via **MQTT Discovery**.

## Basis / Credits
This add-on packages and automates the upstream project:
- Upstream: `Johnny100dk/aduro2mqtt` (MQTT bridge & logic)  
- Inspiration/Fork history: `freol35241/aduro2mqtt`

## Idea
- **Add-on** instead of a custom Docker setup: one-click install right from the HA Add-on Store.  
- **Auto detection (MQTT Discovery)**: Sensors, switch and selects are created automatically in the **MQTT integration** (and cleaned up when needed).

---

## Requirements
- Home Assistant (Supervised/OS)
- **MQTT broker** (recommended: **Mosquitto** add-on)
- Network access to the Aduro boiler (IP), serial number & PIN

---

## Installation (Step by step)

1) **Install MQTT broker**  
   - Add-on Store → install & start **Mosquitto broker**.  
   - In **Settings → Devices & Services → MQTT**, ensure the integration is set up (discovery enabled).

2) **Add add-on repository**  
   - Add-on Store → top-right **⋮ → Repositories** → add your Aduro2MQTT repository URL.  
   - **Aduro2MQTT** will then appear in the store.

3) **Create a dedicated MQTT user (recommended)**  
   - Settings → People & Zones → **Users** → create a new user (e.g. `aduro`) with a **strong password**.  
   - If needed, grant credentials in Mosquitto (default HA setup handles this).

4) **Install & configure the Aduro2MQTT add-on**  
   - Open the add-on → **Configuration**:
     - **MQTT**
       - `mqtt_host`: `core-mosquitto` (when using Mosquitto add-on) or your broker’s host/IP  
       - `mqtt_port`: `1883`  
       - `mqtt_client_id`: e.g. `aduro2mqtt`  
       - `mqtt_user` / `mqtt_password`: **the user created above**
       - `mqtt_base_topic`: `aduro2mqtt` (default)
     - **Aduro**
       - `aduro_host`: IP of your boiler (e.g. `192.168.x.y`)  
       - `aduro_serial`: serial number  
       - `aduro_pin`: PIN  
       - `aduro_poll_interval`: e.g. `30` seconds
     - **Discovery (optional)**
       - `discovery_enable`: `true`  
       - `discovery_prefix`: `homeassistant`  
       - `device_name`: `Aduro H2`  
       - `device_id`: `aduro_h2`  
       - `discovery_exclude`: list of keys you **don’t** want to publish (e.g. `boiler_pump_state`, `return_temp`)
   - **Save** → **Start**.

5) **Devices/entities appear automatically**  
   - Home Assistant → **Settings → Devices & Services → MQTT**  
   - You should see a **device “Aduro H2”** with sensors/entities (temperatures, power, exhaust speed, CO, …).  
   - A **switch** (“Aduro H2 Toggle”) and a **select** (“Fixed power (%)”) are provided via discovery.

---

## Example configuration (Add-on → “Configuration”)
```yaml
mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_client_id: aduro2mqtt
mqtt_user: aduro
mqtt_password: !secret mqtt_aduro_password
mqtt_base_topic: aduro2mqtt

aduro_host: 192.168.177.74
aduro_serial: "84956"
aduro_pin: "4438539130"
aduro_poll_interval: 30

discovery_enable: true
discovery_prefix: homeassistant
device_name: Aduro H2
device_id: aduro_h2
discovery_exclude:
  - boiler_pump_state
  - return_temp

log_level: INFO
```

---

## What gets created?
- **Sensors** (selection):  
  - `Room Temp`, `Shaft Temp`, `Smoke Temp`, `Oxygen`, `Power Pct`, `Exhaust Speed`, `CO (ppm)`, `Total Hours`  
- **Switch**:  
  - “Aduro H2 Toggle” (Start/Stop)  
- **Select**:  
  - “Fixed power (%)” (10/50/100)

> Note: The sensor set is deliberately curated. Use `discovery_exclude` to hide individual keys.

---

## Tips & Troubleshooting
- **No devices visible?**  
  - Is the MQTT integration active in HA?  
  - Correct broker login (`mqtt_user`/`mqtt_password`)?  
  - Add-on logs should show lines like “publish …/config”.
- **CO value shows 0?**  
  - The boiler may report `0` while idle. Check during operation.  
- **Boiler not responding?**  
  - Check network/IP, serial & PIN, optionally increase poll interval to 60 s.

---

## License & Credits
- This add-on bundles the work of `Johnny100dk/aduro2mqtt` (observe the upstream license).  
- Thanks to community forks (incl. `freol35241`) for ideas & examples.
