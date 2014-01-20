from django.db import models


class Bar(models.Model):
    name = models.CharField(max_length=5)

    class Meta:
        app_label = 'complex_app'
