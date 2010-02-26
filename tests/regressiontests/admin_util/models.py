from django.db import models


class Count(models.Model):
    num = models.PositiveSmallIntegerField()
