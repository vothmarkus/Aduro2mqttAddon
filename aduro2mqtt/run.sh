#!/usr/bin/with-contenv bash
set -euo pipefail

OPTIONS_FILE="/data/options.json"
jqr() { jq -r "${1}" "${OPTIONS_FILE}" 2>/dev/null; }

MQTT_HOST=$(jqr '.mqtt_host // "core-mosquitto"')
MQTT_PORT=$(jqr '.mqtt_port // 1883')
MQTT_CLIENT_ID=$(jqr '.mqtt_client_id // "aduro2mqtt"')
MQTT_USER=$(jqr '.mqtt_user // ""')
MQTT_PASSWORD=$(jqr '.mqtt_password // ""')
MQTT_BASE_TOPIC=$(jqr '.mqtt_base_topic // "aduro2mqtt"')

ADURO_HOST=$(jqr '.aduro_host // ""')
ADURO_SERIAL=$(jqr '.aduro_serial // ""')
ADURO_PIN=$(jqr '.aduro_pin // ""')
ADURO_POLL_INTERVAL=$(jqr '.aduro_poll_interval // 30')

DISCOVERY_ENABLE=$(jqr '.discovery_enable // true')
DISCOVERY_PREFIX=$(jqr '.discovery_prefix // "homeassistant"')
DEVICE_NAME=$(jqr '.device_name // "Aduro H2"')
DEVICE_ID=$(jqr '.device_id // "aduro_h2"')
DISCOVERY_EXCLUDE=$(jq -r '[.discovery_exclude[]?] | join(",")' "${OPTIONS_FILE}" 2>/dev/null || echo "boiler_pump_state,return_temp")
[ -z "${DISCOVERY_EXCLUDE}" ] && DISCOVERY_EXCLUDE="boiler_pump_state,return_temp"

LOG_LEVEL=$(jqr '.log_level // "INFO"')

echo "[INFO] MQTT: host=${MQTT_HOST}, port=${MQTT_PORT}, user=${MQTT_USER:-<none>}"
echo "[INFO] Discovery: ${DISCOVERY_ENABLE} (prefix=${DISCOVERY_PREFIX}, device=${DEVICE_NAME}/${DEVICE_ID}, exclude=${DISCOVERY_EXCLUDE})"
echo "[INFO] Starte aduro2mqtt: MQTT @ ${MQTT_HOST}:${MQTT_PORT}, Aduro @ ${ADURO_HOST}, Poll=${ADURO_POLL_INTERVAL}s"

export MQTT_HOST MQTT_PORT MQTT_USER MQTT_PASSWORD MQTT_BASE_TOPIC MQTT_CLIENT_ID
export ADURO_HOST ADURO_SERIAL ADURO_PIN ADURO_POLL_INTERVAL
export LOG_LEVEL
export DISCOVERY_PREFIX BASE_TOPIC="${MQTT_BASE_TOPIC}" DEVICE_NAME DEVICE_ID DISCOVERY_EXCLUDE
export PYTHONWARNINGS="ignore::ResourceWarning"

if [ "${DISCOVERY_ENABLE}" = "true" ] || [ "${DISCOVERY_ENABLE}" = "True" ]; then
  /opt/venv/bin/python /opt/discovery.py || echo "[WARN] Discovery failed (continuing)"
fi

BACKOFF=5
MAX_BACKOFF=60

while true; do
  /opt/venv/bin/python /opt/aduro2mqtt/main.py || true
  RC=$?
  if [ $RC -eq 0 ]; then
    echo "[INFO] aduro2mqtt exited cleanly."
    exit 0
  fi
  echo "[ERROR] aduro2mqtt exited with code ${RC}. Restart in ${BACKOFF}s..."
  sleep "${BACKOFF}"
  BACKOFF=$(( BACKOFF < MAX_BACKOFF ? BACKOFF * 2 : MAX_BACKOFF ))
done
