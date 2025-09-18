ARG BUILD_FROM=ghcr.io/home-assistant/{arch}-base:latest
FROM $BUILD_FROM

ARG UPSTREAM_REPO="https://github.com/Johnny100dk/aduro2mqtt.git"

RUN apk add --no-cache python3 py3-pip git
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /opt
RUN git clone ${UPSTREAM_REPO} aduro2mqtt
WORKDIR /opt/aduro2mqtt

RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD [ "/run.sh" ]
