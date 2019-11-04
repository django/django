import os

from django.apps import AppConfig


class NSAppConfig(AppConfig):
    name = 'nsapp'
    path = os.path.dirname(__file__)
