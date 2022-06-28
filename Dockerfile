FROM ubuntu:20.04
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

ADD requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

RUN mkdir -p /opt/app/

ENV DATADIR=/DATA
RUN mkdir -p $DATADIR

ENV DICOM_ENDPOINTS=/DICOM_ENDPOINTS
RUN mkdir -p $DICOM_ENDPOINTS

WORKDIR /opt/app/
COPY . /opt/app/

CMD /usr/bin/python3 main.py
