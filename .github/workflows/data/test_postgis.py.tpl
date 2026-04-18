from test_sqlite import *  # NOQA

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "USER": "user",
        "NAME": "geodjango",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": 5432,
    },
    "other": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "USER": "user",
        "NAME": "geodjango2",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": 5432,
    },
}
