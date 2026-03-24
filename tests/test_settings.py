# tests/test_settings.py
SECRET_KEY = 'test-secret-key'
ROOT_URLCONF = 'tests.test_urls'  # we'll create this next
DEBUG = True
ALLOWED_HOSTS = ['*']

# Minimal databases if you use TransactionTestCase later
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}