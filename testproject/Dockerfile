FROM ubuntu:16.04

MAINTAINER Andrew Godwin <andrew@aeracode.org>

RUN apt-get update && \
    apt-get install -y \
        git \
        python-dev \
        python-setuptools \
        python-pip && \
    pip install -U pip

RUN pip install channels==0.9.5 asgi_redis==0.8.3

RUN git clone https://github.com/andrewgodwin/channels.git /srv/application/

WORKDIR /srv/application/testproject/

EXPOSE 80
