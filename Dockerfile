FROM ubuntu:20.04
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

ADD requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

RUN mkdir -p /opt/app/

ENV INCOMING_DIR=/INCOMING
ENV SCP_CONFIG_JSON=/CONFIGURATION/SCP/scp.json
ENV FINGERPRINT_DIR=/CONFIGURATION/FINGERPRINTS
ENV CERT_FILE=/CONFIGURATION/CERTS/cert.crt

RUN mkdir -p $INCOMING_DIR $FINGERPRINT_DIR

WORKDIR /opt/app/
COPY . /opt/app/

CMD /usr/bin/python3 src/main.py
