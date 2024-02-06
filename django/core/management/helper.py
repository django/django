from django import setup
from django.apps import apps
from django.utils.module_loading import import_string

DJANGO_DEFAULT_IMPORTS = [
    "from django.core.cache import cache",
    "from django.conf import settings",
    "from django.contrib.auth import get_user_model",
    "from django.db import transaction",
    "from django.db.modelfrom django.utils.module_loading import import_strings import Avg, Case, Count, F, Max, Min, Prefetch, Q, Sum, When",
    "from django.utils import timezone",
    "from django.urls import reverse",
    "from django.db.models import Exists, OuterRef, Subquery",
]

CHANGED_IMPORTS = [
    {"cache": "django.core.cache.cache"},
    {"settings": "django.conf.settings"},
    {"get_user_model": "django.contrib.auth.get_user_model"},
    {"transaction": "django.db.transaction"},
    {"Avg": "django.db.models.Avg"},
    {"Case": "django.db.models.Case"},
    {"Count": "django.db.models.Count"},
    {"F": "django.db.models.F"},
    {"Max": "django.db.models.Max"},
    {"Min": "django.db.models.Min"},
    {"Prefetch": "django.db.models.Prefetch"},
    {"Q": "django.db.models.Q"},
    {"Sum": "django.db.models.Sum"},
    {"When": "django.db.models.When"},
    {"timezone": "django.utils.timezone"},
    {"reverse": "django.urls.reverse"},
    {"Exists": "django.db.models.Exists"},
]


def get_objects(style):
    import_objects = {}
    for x in CHANGED_IMPORTS:
        for key, val in x.items():
            import_objects[key] = import_string(val)
    print(style.MIGRATE_HEADING("# Importing Necessary modules"))
    for x in DJANGO_DEFAULT_IMPORTS:
        print(style.SUCCESS(x))
    return import_objects


if not apps.ready:
    setup()


def get_apps_and_models():
    for app in apps.get_app_configs():
        if app.models_module:
            yield app.models_module, app.get_models()


def get_app_models(load_models, style):
    import_objects = {}
    print(style.MIGRATE_HEADING("# Importing all apps models"))
    for key, val in load_models.items():
        if len(val) >= 1:
            for x in val:
                print(style.SUCCESS(f"from {key} import {x}"))
                import_objects[x] = import_string(str(key) + "." + str(x))
    return import_objects
