from django.apps.cache import BaseAppCache
from django.db import models

# We're testing app cache presence on load, so this is handy.

new_app_cache = BaseAppCache()


class TotallyNormal(models.Model):
    name = models.CharField(max_length=255)


class SoAlternative(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        app_cache = new_app_cache
