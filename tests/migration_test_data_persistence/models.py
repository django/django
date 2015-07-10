from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=100)


class Unmanaged(models.Model):
    title = models.CharField(max_length=100)

    class Meta:
        managed = False
