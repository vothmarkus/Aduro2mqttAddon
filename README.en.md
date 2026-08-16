# Aduro – native Home Assistant integration

<img src="custom_components/aduro/brand/logo.png" alt="Aduro project logo" width="150"/>

- 🇩🇪 **Deutsch:** [README.md](README.md)

This integration connects an **Aduro H2**, or a compatible NBE controller,
directly to Home Assistant. It replaces the legacy Aduro2MQTT bridge, so no
MQTT broker, add-on, or MQTT Discovery setup is required.

## Features

All Home Assistant features exposed by the previous add-on are retained:

| Feature | Native Home Assistant entity |
|---|---|
| Target and current temperature | Climate |
| Automatic and fixed-power operation | Climate mode |
| Start/stop heating | Switch |
| Fixed power at 10/50/100% | Select |
| Force auger for 0–120 seconds | Number |
| Smoke and room temperature | Sensor |
| Operating state and raw state numbers | Sensor |
| State duration and current power | Sensor |

The raw sensors disabled by default in the legacy add-on remain available but
start disabled: **room temperature**, **state number**, **substate number**, and
**state duration**. Enable them from **Device → Entities** when needed.

After each command, the integration waits 0.6 seconds and immediately refreshes
the stove data, matching the previous behavior. The regular polling interval is
30 seconds by default.

## HACS installation

1. Add this repository to HACS as a custom **Integration** repository.
2. Install **Aduro**.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → Aduro**.
5. Enter the device name, local IP/host name, serial number, and PIN.

The setup flow verifies the connection. Host, PIN, and polling interval can be
changed later through **Configure**.

## Migrating from the add-on

> Stop the Aduro2MQTT add-on before configuring the native integration.

PyDuro binds UDP requests to local port 1901, so the add-on and native
integration must not run at the same time.

Recommended order:

1. Note entity names and automations using the MQTT entities.
2. Stop, but do not yet uninstall, the Aduro2MQTT add-on.
3. Configure and verify the native Aduro integration.
4. Point automations to the new native entities.
5. Remove the old MQTT Discovery entities and then uninstall the add-on.

## Architecture

- local NBE UDP communication without MQTT
- PyDuro 3.2.1 protocol dependency
- one central DataUpdateCoordinator
- process-wide serialization of UDP calls because PyDuro uses port 1901
- UI configuration and options flow
- stable device/entity identifiers derived from the controller serial number
- automatic offline handling and polling recovery

## License and credits

Apache License 2.0. The integration retains the behavior established by
[Johnny100dk/aduro2mqtt](https://github.com/Johnny100dk/aduro2mqtt) and uses
[PyDuro](https://github.com/clementprevot/pyduro), an external MIT-licensed
dependency. See [NOTICE](NOTICE) for details.
