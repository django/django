from django.db import models


class SomeObject(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        app_label = "messages"

    def __str__(self):
        return self.name
