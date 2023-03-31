#!/bin/bash
rm db.sqlite3
export DJANGO_SUPERUSER_PASSWORD=test
python manage.py migrate
python manage.py createsuperuser --no-input --username test --email test@test.com
python manage.py migrate
python manage.py migrate rmigrate zero
