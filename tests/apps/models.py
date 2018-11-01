from django.apps.registry import Apps
from django.db import models

# We're testing app registry presence on load, so this is handy.

new_apps = Apps(['apps'])


class TotallyNormal(models.Model):
    name = models.CharField(max_length=255)


class SoAlternative(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        apps = new_apps
