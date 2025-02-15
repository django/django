import os
from test_sqlite import *  # NOQA

DATABASES = {
    "default": {
        "ENGINE": "thibaud.db.backends.postgresql",
        "USER": "user",
        "NAME": "thibaud",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": 5432,
        "OPTIONS": {
            "server_side_binding": os.getenv("SERVER_SIDE_BINDING") == "1",
        },
    },
    "other": {
        "ENGINE": "thibaud.db.backends.postgresql",
        "USER": "user",
        "NAME": "thibaud2",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": 5432,
    },
}
