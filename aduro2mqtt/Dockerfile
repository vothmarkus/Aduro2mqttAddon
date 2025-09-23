ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# System-Pakete
RUN apk add --no-cache python3 py3-pip git jq

# Virtuelle Umgebung gegen PEP668-Fehler
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONWARNINGS="ignore::ResourceWarning"

# Upstream holen
WORKDIR /opt
RUN git clone https://github.com/Johnny100dk/aduro2mqtt.git aduro2mqtt

# Python-Abhängigkeiten (mit Constraints, damit z.B. paho-mqtt-Version passt)
COPY constraints.txt /opt/constraints.txt
WORKDIR /opt/aduro2mqtt
RUN if [ -f requirements.txt ]; then \
      pip install --no-cache-dir --upgrade pip && \
      pip install --no-cache-dir -r requirements.txt -c /opt/constraints.txt ; \
    fi

# Add-on Helfer
WORKDIR /opt
COPY discovery.py /opt/discovery.py
COPY refresh_on_set.py /opt/refresh_on_set.py
COPY run.sh /run.sh
# ausführbar machen
RUN chmod +x /run.sh /opt/discovery.py /opt/refresh_on_set.py

# Labels (optional)
LABEL io.hass.name="Aduro2MQTT" \
      io.hass.description="MQTT bridge for Aduro H2 with Discovery" \
      io.hass.type="addon" \
      io.hass.arch="amd64"

# Start
CMD ["/run.sh"]
