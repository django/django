FROM ubuntu:16.04

MAINTAINER Andrew Godwin <andrew@aeracode.org>

# python-dev \
RUN apt-get update && \
    apt-get install -y \
        git \
        python-setuptools \
        python-pip && \
    pip install -U pip

# Install asgi_redis driver and most recent Daphne
RUN pip install \
    asgi_redis==0.8.3 \
    git+https://github.com/andrewgodwin/daphne.git@#egg=daphne

# Clone Channels and install it
RUN git clone https://github.com/andrewgodwin/channels.git /srv/channels/ && \
    cd /srv/channels && \
    git reset --hard caa589ae708a1a66ba1bdcd24f5fd473040772bd && \
    python setup.py install

WORKDIR /srv/channels/testproject/
ENV REDIS_URL=redis://redis:6379

EXPOSE 80
