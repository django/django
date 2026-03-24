# tests/test_settings.py

SECRET_KEY = 'dummy-secret-key-for-tests'
DEBUG = True
ALLOWED_HOSTS = ['*']

# Dummy database to avoid database-related errors
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.dummy',
    }
}