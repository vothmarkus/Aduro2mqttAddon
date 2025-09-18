# Aduro2MQTT (Home Assistant Add-on)

Dieses Add-on verpackt das Upstream-Projekt **aduro2mqtt** in ein Home-Assistant-Add-on.
Es verbindet einen Aduro/NBE-Ofen via UDP mit MQTT.

## Konfiguration
Siehe `config.yaml` (Options & Schema). Logs können per `log_level: DEBUG` ausführlicher gemacht werden.

## Build-Hinweise
- Venv (`/opt/venv`) wird genutzt, um PEP 668 Konflikte zu vermeiden.
- `ARG BUILD_FROM=ghcr.io/home-assistant/{arch}-base:latest` ist für alle Architekturen korrekt.
