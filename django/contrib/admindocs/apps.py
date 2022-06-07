from django.apps import AppConfig
from django.urls import get_resolver, get_urlconf
from django.utils.translation import gettext_lazy as _

from .utils import _active, register_callback


class AdminDocsConfig(AppConfig):
    name = "django.contrib.admindocs"
    verbose_name = _("Administrative Documentation")

    def ready(self):
        urlconf = get_urlconf()
        urlresolver = get_resolver(urlconf)
        register_callback(urlresolver, _active.local_value)
