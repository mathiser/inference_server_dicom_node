FROM ubuntu:20.04
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

ADD requirements /requirements
RUN pip install -r /requirements

RUN mkdir -p /opt/app/

WORKDIR /opt/app/
COPY . /opt/app/

CMD /usr/bin/python3 src/main.py
