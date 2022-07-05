FROM ubuntu:20.04
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

ADD requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

RUN mkdir -p /opt/app/

ENV SCP_HOSTNAME=localhost
ENV SCP_PORT=104
ENV SCP_AE_TITLE=DICOM_NODE
ENV INCOMING_DIR=/INCOMING
ENV FINGERPRINT_DIR=/CONFIGURATION/FINGERPRINTS
ENV CERT_FILE=/CONFIGURATION/CERTS/cert.crt
ENV PYNETDICOM_LOG_LEVEL=none
ENV RUN_INTERVAL=1
ENV SEND_AFTER=10
ENV GET_TIMEOUT=86400
ENV DELETE_ON_SEND=true

RUN mkdir -p $INCOMING_DIR $FINGERPRINT_DIR

WORKDIR /opt/app/
COPY . /opt/app/

CMD /usr/bin/python3 src/main.py
