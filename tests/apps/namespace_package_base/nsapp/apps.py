import os

from freedom.apps import AppConfig
from freedom.utils._os import upath


class NSAppConfig(AppConfig):
    name = 'nsapp'
    path = upath(os.path.dirname(__file__))
