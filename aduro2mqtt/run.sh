#!/usr/bin/with-contenv bashio
set -euo pipefail

# Suppress ResourceWarnings for unclosed sockets
export PYTHONWARNINGS="ignore::ResourceWarning"
export PYTHONUNBUFFERED=1

MQTT_HOST="$(bashio::config 'mqtt_host')"
MQTT_PORT="$(bashio::config 'mqtt_port')"
MQTT_CLIENT_ID="$(bashio::config 'mqtt_client_id')"
MQTT_USER="$(bashio::config 'mqtt_user')"
MQTT_PASSWORD="$(bashio::config 'mqtt_password')"
MQTT_BASE_TOPIC="$(bashio::config 'mqtt_base_topic')"

ADURO_HOST="$(bashio::config 'aduro_host')"
ADURO_SERIAL="$(bashio::config 'aduro_serial')"
ADURO_PIN="$(bashio::config 'aduro_pin')"
ADURO_POLL_INTERVAL="$(bashio::config 'aduro_poll_interval')"

LOG_LEVEL="$(bashio::config 'log_level')"

if [[ -z "${MQTT_HOST}" || -z "${ADURO_HOST}" || -z "${ADURO_SERIAL}" || -z "${ADURO_PIN}" ]]; then
  bashio::log.fatal "Fehlende Optionen: mqtt_host/aduro_host/aduro_serial/aduro_pin."
  exit 1
fi

export MQTT_BROKER_HOST="${MQTT_HOST}"
export MQTT_BROKER_PORT="${MQTT_PORT:-1883}"
export MQTT_CLIENT_ID="${MQTT_CLIENT_ID:-aduro2mqtt}"
[[ -n "${MQTT_USER:-}" && "${MQTT_USER}" != "null" ]] && export MQTT_USER="${MQTT_USER}"
[[ -n "${MQTT_PASSWORD:-}" && "${MQTT_PASSWORD}" != "null" ]] && export MQTT_PASSWORD="${MQTT_PASSWORD}"
export MQTT_BASE_TOPIC="${MQTT_BASE_TOPIC:-aduro2mqtt}"

export ADURO_HOST="${ADURO_HOST}"
export ADURO_SERIAL="${ADURO_SERIAL}"
export ADURO_PIN="${ADURO_PIN}"
export ADURO_POLL_INTERVAL="${ADURO_POLL_INTERVAL:-30}"

export LOG_LEVEL="${LOG_LEVEL:-INFO}"

bashio::log.info "Starte aduro2mqtt: MQTT @ ${MQTT_BROKER_HOST}:${MQTT_BROKER_PORT}, Aduro @ ${ADURO_HOST}, Poll=${ADURO_POLL_INTERVAL}s"

cd /opt/aduro2mqtt
if [[ -f "main.py" ]]; then
  exec /opt/venv/bin/python3 main.py
elif [[ -f "aduro2mqtt.py" ]]; then
  exec /opt/venv/bin/python3 aduro2mqtt.py
else
  bashio::log.fatal "Konnte keinen Startpunkt (main.py/aduro2mqtt.py) im Upstream-Repo finden."
  ls -la
  exit 1
fi
