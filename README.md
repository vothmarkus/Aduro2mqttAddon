# Aduro2MQTT Add-on (with pruned Discovery)

This folder contains the **changed files** for your existing add-on:
- `discovery.py` – publishes HA MQTT Discovery only for the useful entities and
  supports `DISCOVERY_EXCLUDE` (default excludes `boiler_pump_state` and `return_temp`).
- `config.yaml` – adds `discovery_exclude` option so you can hide more entities without editing code.
- `README.md` – this file.

## Usage

1. Copy the files in this folder over the same files in your repository at `aduro2mqtt/`.
2. Rebuild/update the add-on in Home Assistant.
3. Restart the add-on. Discovery will republish the entities (pruned list).

### Options (excerpt)

```yaml
discovery_enable: true
discovery_prefix: "homeassistant"
device_name: "Aduro H2"
device_id: "aduro_h2"

# Hide entities (IDs from discovery.py keys)
discovery_exclude:
  - boiler_pump_state
  - return_temp
```

### CO Sensor
`aduro2mqtt/status` contains `drift.co`. The discovery maps it to the **Co** sensor (ppm).
If your stove reports `0`, you'll see `0 ppm` – that's expected while idle.

---