DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "django_in_any",
        "USER": "jimmyyeung",
        "HOST": "localhost",
        "PORT": 5432,
    },
    "other": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "django_in_any_other",
        "USER": "jimmyyeung",
        "HOST": "localhost",
        "PORT": 5432,
    },
}
SECRET_KEY = "test-in-as-any"
USE_TZ = False
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
]
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
