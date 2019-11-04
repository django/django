from django.db import models


class Bar(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        app_label = 'app_waiting_migration'
