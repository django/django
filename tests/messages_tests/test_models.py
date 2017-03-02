from django.db import models


class SomeObjects(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        app_level = "messages"

    def __str__(self):
        return self.name
