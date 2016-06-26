from __future__ import unicode_literals

from django.db import models


class Foo(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Foo"
