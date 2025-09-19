ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-pip git jq

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /opt
RUN git clone https://github.com/Johnny100dk/aduro2mqtt.git aduro2mqtt

COPY constraints.txt /opt/constraints.txt
WORKDIR /opt/aduro2mqtt
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt -c /opt/constraints.txt; fi

WORKDIR /opt
COPY discovery.py /opt/discovery.py
COPY run.sh /run.sh
RUN chmod +x /run.sh /opt/discovery.py

LABEL io.hass.name="Aduro2MQTT" io.hass.description="MQTT bridge for Aduro H2 with Discovery" io.hass.type="addon" io.hass.arch="amd64"

CMD ["/run.sh"]
