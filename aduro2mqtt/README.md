# Aduro2MQTT (Home Assistant Add-on)

Dieses Add-on verpackt das Upstream-Projekt **aduro2mqtt** in ein Home‑Assistant‑Add‑on.
Es verbindet einen Aduro/NBE-Ofen via UDP mit MQTT.

## Konfiguration

| Option              | Typ       | Beschreibung                                   |
|---------------------|-----------|-----------------------------------------------|
| `mqtt_host`         | string    | MQTT Broker Hostname/IP                        |
| `mqtt_port`         | int       | MQTT Port (Default: 1883)                      |
| `mqtt_client_id`    | string?   | Optionaler Client-ID                           |
| `mqtt_user`         | string?   | MQTT Benutzername                              |
| `mqtt_password`     | password? | MQTT Passwort                                  |
| `mqtt_base_topic`   | string    | Basistopic (Default: `aduro2mqtt`)             |
| `aduro_host`        | string    | IP/Host des Aduro/NBE-Geräts                   |
| `aduro_serial`      | string    | Seriennummer des Geräts                        |
| `aduro_pin`         | string    | PIN des Geräts                                 |
| `aduro_poll_interval` | int     | Poll-Intervall in Sekunden (Default: 30)       |
| `log_level`         | enum      | `WARNING`, `INFO` oder `DEBUG`                 |

> Hinweis: Falls die UDP-Kommunikation Probleme macht, kann testweise `host_network` in `config.yaml` auf `true` gestellt werden.

## Installation (lokal)
1. Ordner `/addons/aduro2mqtt` erstellen und Inhalte aus diesem Verzeichnis hinein kopieren.
2. In Home Assistant: **Settings → Add-ons → Add-on Store → ⋮ → Check for updates**.  
   Danach unter **Local add-ons** *Aduro2MQTT* öffnen.
3. Optionen ausfüllen → **Save** → **Start**. Logs prüfen und ggf. `log_level: DEBUG` setzen.

## Build-Hinweise
- Das Dockerfile erlaubt per Build-Arg `UPSTREAM_REPO` das Upstream-Repository zu wechseln (Default: `Johnny100dk/aduro2mqtt`).
- Das Basisimage wird vom Supervisor via `BUILD_FROM` gesetzt.
