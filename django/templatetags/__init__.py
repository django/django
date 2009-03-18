from django.conf import settings
from django.utils import importlib

for a in settings.INSTALLED_APPS:
    try:
        __path__.extend(importlib.import_module('.templatetags', a).__path__)
    except ImportError:
        pass
