DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # Use in-memory SQLite DB for fast testing
    }
}

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.sites',
    'tests',  # Ensure the test app is included
    
]
MIDDLEWARE = []

SECRET_KEY = "dummy-secret-key"

SITE_ID = 1  # Required for `django.contrib.sites`
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
