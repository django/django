#!/bin/bash
set -e

python3 -m venv .venv
. .venv/bin/activate
pip install -U pip setuptools wheel
pip install -e .

# django-admin startproject hello_django
# cd hello_django
# python manage.py migrate