from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ImportmapConfig(AppConfig):
    name = "django.contrib.importmap"
    verbose_name = _("HTML importmap managment")
    importmaps = None

    def ready(self):
        from django.contrib.importmap.base import get_importmaps

        self.importmaps = get_importmaps()
