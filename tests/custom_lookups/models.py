from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=20)
    age = models.IntegerField(null=True)
    birthdate = models.DateField(null=True)
