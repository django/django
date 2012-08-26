from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Village(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Population(models.Model):
    village = models.ForeignKey(Village)
    total = models.IntegerField()

    def __str__(self):
        return self.village.name


@python_2_unicode_compatible
class City(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Weather(models.Model):
    city = models.ForeignKey(City)
    temp = models.IntegerField()

    def __str__(self):
        return self.city.name
