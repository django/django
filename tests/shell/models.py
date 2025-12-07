from django.db import models


class Marker(models.Model):
    pass


class Phone(models.Model):
    name = models.CharField(max_length=50)
