ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
          libmemcached-dev \
          build-essential \
          libsqlite3-mod-spatialite binutils libproj-dev gdal-bin libgdal20 libgeoip1 \
          default-libmysqlclient-dev default-mysql-client \
          unzip libaio1 \
          gettext \
          wget git \
    && apt-get clean

RUN groupadd -r test && useradd --no-log-init -r -g test test

RUN mkdir /geolite2/ \
    && cd /geolite2/ \
    && wget -q http://geolite.maxmind.com/download/geoip/database/GeoLite2-City.tar.gz \
        http://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.tar.gz \
    && (cat *.tar.gz | tar zxvf - --wildcards "*.mmdb" --strip-components=1 -i) \
    && rm *.tar.gz \
    && cd /

RUN wget -q https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh -O /bin/wait-for-it.sh \
    && chmod a+x /bin/wait-for-it.sh

ENV PIP_NO_CACHE_DIR=off
ENV PYTHONDONTWRITEBYTECODE=1
RUN pip install --upgrade pip

COPY ./tests/requirements /tmp/requirements
RUN for f in /tmp/requirements/*.txt; do pip install -r $f; done && \
    pip install flake8 flake8-isort selenium

ENV PYTHONPATH "${PYTHONPATH}:/django/:/django/docker/"
USER test:test
WORKDIR /django
VOLUME /django

