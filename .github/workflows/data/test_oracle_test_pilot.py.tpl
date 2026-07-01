import os
from test_sqlite import *  # NOQA

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
