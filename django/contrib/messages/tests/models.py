from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class SomeObject(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        app_label = "messages"

    def __str__(self):
        return self.name
