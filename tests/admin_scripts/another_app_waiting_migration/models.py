from __future__ import unicode_literals

from django.db import models


class Foo(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        app_label = 'another_app_waiting_migration'
