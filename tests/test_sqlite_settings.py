DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.sites",
    "tests",
]
MIDDLEWARE = []

SECRET_KEY = "dummy-secret-key"

SITE_ID = 1
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
