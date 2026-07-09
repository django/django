DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "django_in_any_bench",
        "USER": "jimmyyeung",
        "HOST": "localhost",
        "PORT": 5432,
    }
}
SECRET_KEY = "bench-in-as-any"
USE_TZ = False
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "postgres_tests",
]
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
