# -*- coding: utf-8 -*-
"""
Production settings for {{ project_name|title }} Django project.

.. note::
    Remember to configure the database and replace all occurences of
    "example.com" with correct values.
"""
from settings import *

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('{{ project_name|title }} Webmaster', 'webmaster@example.com'),
)
MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '{{ project_name }}',               # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': '{{ project_name }}',
        'PASSWORD': '{% for r in ''|center:20 %}{{ secret_key|safe|random }}{% endfor %}',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
        'SCHEMA': '',                    # Can be used with PostgreSQL.
    }
}

SECRET_KEY = '{{ secret_key|safe }}'

EMAIL_HOST = 'mail.example.com'
DEFAULT_FROM_EMAIL = '{{ project_name|title }} Webmaster <webmaster@example.com>'
SERVER_EMAIL = DEFAULT_FROM_EMAIL

