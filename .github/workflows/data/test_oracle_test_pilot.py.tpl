import os

CONNECTION_STRING = os.environ.get("TESTPILOT_CONNECTION_STRING_SUFFIX", "")
RUNID = os.environ.get("RUNID", "")
PASSWORD = os.environ.get("TESTPILOT_PASSWORD", "")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.oracle",
        "NAME": CONNECTION_STRING,
        "USER": "django_tests_default_" + RUNID,
        "PASSWORD": PASSWORD,
        "TEST": {
            "CREATE_DB": False,
            "CREATE_USER": False,
            "USER": "django_tests_default_" + RUNID,
            "PASSWORD": PASSWORD,
        },
    },
    "other": {
        "ENGINE": "django.db.backends.oracle",
        "NAME": CONNECTION_STRING,
        "USER": "django_tests_other_" + RUNID,
        "PASSWORD": PASSWORD,
        "TEST": {
            "CREATE_DB": False,
            "CREATE_USER": False,
            "USER": "django_tests_other_" + RUNID,
            "PASSWORD": PASSWORD,
        },
    },
}

SECRET_KEY = "django_tests_secret_key"

# Use a fast hasher to speed up tests.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

USE_TZ = False
