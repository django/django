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
    asgi_redis==1.0.0 \
    git+https://github.com/django/daphne.git@#egg=daphne

# Clone Channels and install it
RUN git clone https://github.com/django/channels.git /srv/channels/ && \
    cd /srv/channels && \
    git reset --hard origin/master && \
    python setup.py install

WORKDIR /srv/channels/testproject/
ENV REDIS_URL=redis://redis:6379

EXPOSE 80
