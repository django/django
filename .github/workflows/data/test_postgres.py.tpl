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

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
    "pylibmc": {
        "BACKEND": "django.core.cache.backends.memcached.PyLibMCCache",
        "LOCATION": "127.0.0.1:11211",
    },
    "pymemcache": {
        "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
        "LOCATION": "127.0.0.1:11211",
    },
}
