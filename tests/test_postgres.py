from django.conf.global_settings import *  # Base settings

SECRET_KEY = 'django_tests_secret_key'
ALLOWED_HOSTS = ['*']
USE_TZ = True
TIME_ZONE = 'UTC'
DEBUG = True

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'get_or_create_race',  # Include your test app here
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'django',
        'USER': 'django',
        'PASSWORD': 'django',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
