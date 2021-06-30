import os

from mango.apps import AppConfig


class NSAppConfig(AppConfig):
    default = False
    name = 'nsapp'
    path = os.path.dirname(__file__)
