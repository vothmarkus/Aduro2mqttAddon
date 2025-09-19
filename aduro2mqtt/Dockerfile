# syntax=docker/dockerfile:1
ARG BUILD_FROM
# fallback for local builds; HA will inject proper BUILD_FROM for each arch
ARG BUILD_FROM_FALLBACK=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM:-$BUILD_FROM_FALLBACK}

# Packages
RUN apk add --no-cache python3 py3-pip git jq

# venv (avoid PEP 668)
RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Upstream
WORKDIR /opt
RUN git clone https://github.com/Johnny100dk/aduro2mqtt.git aduro2mqtt

# Python deps + pins
COPY constraints.txt /opt/constraints.txt
RUN pip install --no-cache-dir --upgrade pip &&     pip install --no-cache-dir -c /opt/constraints.txt -r /opt/aduro2mqtt/requirements.txt

# Our files
COPY run.sh /opt/run.sh
COPY discovery.py /opt/discovery.py
RUN chmod +x /opt/run.sh

# s6 service (create inline to keep repo flat)
RUN mkdir -p /etc/services.d/aduro2mqtt &&     printf '#!/usr/bin/execlineb -P\nwith-contenv\n/opt/run.sh\n' > /etc/services.d/aduro2mqtt/run &&     chmod +x /etc/services.d/aduro2mqtt/run
