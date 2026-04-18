import os
from test_sqlite import *  # NOQA

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "USER": "user",
        "NAME": "django",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": 5432,
        "OPTIONS": {
            "server_side_binding": os.getenv("SERVER_SIDE_BINDING") == "1",
        },
    },
    "other": {
        "ENGINE": "django.db.backends.postgresql",
        "USER": "user",
        "NAME": "django2",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": 5432,
    },
}
