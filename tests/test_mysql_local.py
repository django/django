DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "django",
        "USER": "root",        # or "django" if you fixed privileges
        "PASSWORD": "secret",  # match whatever you set in Docker
        "HOST": "127.0.0.1",
        "PORT": "3306",
    },
    "other": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "django",
        "USER": "root",
        "PASSWORD": "secret",
        "HOST": "127.0.0.1",
        "PORT": "3306",
    },
}

SECRET_KEY = "test"
USE_TZ = False