#!/usr/bin/with-contenv bash
set -euo pipefail

OPT="/data/options.json"

val() { jq -er "$1" "$OPT"; }
val_or() { jq -er "$1 // $2" "$OPT"; }

MQTT_HOST=$(val '.mqtt_host')
MQTT_PORT=$(val_or '.mqtt_port' 1883)
MQTT_CLIENT_ID=$(val '.mqtt_client_id')
MQTT_USER=$(jq -er '.mqtt_user // empty' "$OPT")
MQTT_PASSWORD=$(jq -er '.mqtt_password // empty' "$OPT")
MQTT_BASE=$(val_or '.mqtt_base_topic' '"aduro2mqtt"')

ADURO_HOST=$(val '.aduro_host')
ADURO_SERIAL=$(val '.aduro_serial')
ADURO_PIN=$(val '.aduro_pin')
ADURO_POLL=$(val_or '.aduro_poll_interval' 30)

LOG_LEVEL=$(val_or '.log_level' '"WARNING"')

DISCOVERY=$(val_or '.discovery' true)
DISCOVERY_PREFIX=$(val_or '.discovery_prefix' '"homeassistant"')
DISCOVERY_DEVICE_NAME=$(val_or '.discovery_device_name' '"Aduro H2"')
DISCOVERY_DEVICE_ID=$(val_or '.discovery_device_id' '"aduro_h2"')
DISCOVERY_CLEANUP=$(val_or '.discovery_cleanup' false)
ENABLE_AUTO_LEARN=$(val_or '.enable_auto_learn' false)
DISCOVERY_LEARN_SECONDS=$(val_or '.discovery_learn_seconds' 8)
DISCOVERY_TOPICS=$(val_or '.discovery_topics' '"status,operating,advanced,settings/+,consumption/#"')

echo "[INFO] MQTT: host=${MQTT_HOST}, port=${MQTT_PORT}, user=${MQTT_USER:+<set>}"
echo "[INFO] Discovery: ${DISCOVERY} (prefix=${DISCOVERY_PREFIX}, device=${DISCOVERY_DEVICE_NAME}/${DISCOVERY_DEVICE_ID}, learn=${DISCOVERY_LEARN_SECONDS}s, topics=${DISCOVERY_TOPICS}, cleanup=${DISCOVERY_CLEANUP})"
echo "[INFO] Starte aduro2mqtt: MQTT @ ${MQTT_HOST}:${MQTT_PORT}, Aduro @ ${ADURO_HOST}, Poll=${ADURO_POLL}s"

export MQTT_BROKER_HOST="${MQTT_HOST}"
export MQTT_BROKER_PORT="${MQTT_PORT}"
export MQTT_USER="${MQTT_USER}"
export MQTT_PASSWORD="${MQTT_PASSWORD}"
export MQTT_CLIENT_ID="${MQTT_CLIENT_ID}"
export MQTT_BASE_TOPIC="${MQTT_BASE}"

export ADURO_HOST="${ADURO_HOST}"
export ADURO_SERIAL="${ADURO_SERIAL}"
export ADURO_PIN="${ADURO_PIN}"
export POLL_INTERVAL="${ADURO_POLL}"

export LOGLEVEL="${LOG_LEVEL}"

# Discovery (optional)
if [ "${DISCOVERY}" = "true" ]; then
    export DISCOVERY_PREFIX="${DISCOVERY_PREFIX}"
    export DEVICE_NAME="${DISCOVERY_DEVICE_NAME}"
    export DEVICE_ID="${DISCOVERY_DEVICE_ID}"
    export DISCOVERY_CLEANUP="${DISCOVERY_CLEANUP}"
    export ENABLE_AUTO_LEARN="${ENABLE_AUTO_LEARN}"
    export DISCOVERY_LEARN_SECONDS="${DISCOVERY_LEARN_SECONDS}"
    export DISCOVERY_TOPICS="${DISCOVERY_TOPICS}"
    python3 /opt/discovery.py || echo "[WARN] discovery failed (continuing)"
fi

# Run upstream app
cd /opt/aduro2mqtt
exec python3 /opt/aduro2mqtt/main.py
