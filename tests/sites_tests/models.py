from django.contrib.sites.models import AbstractBaseSite
from django.db import models

__all__ = ('CustomSite',)


class CustomSite(AbstractBaseSite):
    alias = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.alias or self.name
