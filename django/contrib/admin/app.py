from django import apps
from django.contrib import admin


class AdminConfig(apps.AppConfig):
    name = 'django.contrib.admin'

    def ready(self):
        admin.autodiscover()
