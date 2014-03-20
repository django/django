import os

from django.apps import AppConfig
from django.utils._os import upath


class NSAppConfig(AppConfig):
    name = 'nsapp'
    path = upath(os.path.dirname(__file__))
