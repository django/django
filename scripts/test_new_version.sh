#! /bin/bash

# Original author: Tim Graham.

set -xue

cd /tmp

RELEASE_VERSION="${VERSION}"
if [[ -z "$RELEASE_VERSION" ]]; then
    echo "Please set VERSION as env var"
    exit 1
fi

PKG_TAR=$(curl -Ls -o /dev/null -w '%{url_effective}' https://www.djangoproject.com/download/$RELEASE_VERSION/tarball/)
echo $PKG_TAR

PKG_WHL=$(curl -Ls -o /dev/null -w '%{url_effective}' https://www.djangoproject.com/download/$RELEASE_VERSION/wheel/)
echo $PKG_WHL

python3 -m venv django-pip
. django-pip/bin/activate
python -m pip install --no-cache-dir $PKG_TAR
django-admin startproject test_one
cd test_one
./manage.py --help  # Ensure executable bits
python manage.py migrate
python manage.py runserver

deactivate
cd ..
rm -rf test_one
rm -rf django-pip


python3 -m venv django-pip-wheel
. django-pip-wheel/bin/activate
python -m pip install --no-cache-dir $PKG_WHL
django-admin startproject test_one
cd test_one
./manage.py --help  # Ensure executable bits
python manage.py migrate
python manage.py runserver

deactivate
cd ..
rm -rf test_one
rm -rf django-pip-wheel
