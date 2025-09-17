# Home Assistant Add-on base image is provided via BUILD_FROM arg
ARG BUILD_FROM
FROM $BUILD_FROM

# Optional: allow overriding the upstream repo at build time
ARG UPSTREAM_REPO="https://github.com/Johnny100dk/aduro2mqtt.git"

# System packages
RUN apk add --no-cache python3 py3-pip git

# Fetch upstream code
WORKDIR /opt
RUN git clone ${UPSTREAM_REPO} aduro2mqtt
WORKDIR /opt/aduro2mqtt

# Python dependencies
# If upstream has requirements.txt; otherwise just ensure pip available
RUN if [ -f requirements.txt ]; then pip3 install --no-cache-dir -r requirements.txt; fi

# Copy start script
COPY run.sh /run.sh
RUN chmod +x /run.sh

# Start
CMD [ "/run.sh" ]
