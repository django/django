from django.db import models


class Simple2(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        app_label = 'app3'
