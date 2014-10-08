from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Author(models.Model):
    name = models.CharField(max_length=20)
    age = models.IntegerField(null=True)
    birthdate = models.DateField(null=True)
    average_rating = models.FloatField(null=True)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class MySQLUnixTimestamp(models.Model):
    timestamp = models.PositiveIntegerField()

    def __str__(self):
        return self.name
