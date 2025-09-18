# Home Assistant Add-on base image (Supervisor will substitute {arch})
ARG BUILD_FROM=ghcr.io/home-assistant/{arch}-base:latest
FROM $BUILD_FROM

# Optional: allow overriding the upstream repo at build time
ARG UPSTREAM_REPO="https://github.com/Johnny100dk/aduro2mqtt.git"

# System packages
RUN apk add --no-cache python3 py3-pip git

# Create a virtual environment to avoid PEP 668 issues
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# Fetch upstream code
WORKDIR /opt
RUN git clone ${UPSTREAM_REPO} aduro2mqtt
WORKDIR /opt/aduro2mqtt

# Python dependencies (install into venv)
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy start script
COPY run.sh /run.sh
RUN chmod +x /run.sh

# Start
CMD [ "/run.sh" ]
