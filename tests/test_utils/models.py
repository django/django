from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Car(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Person(models.Model):
    name = models.CharField(max_length=100)
    cars = models.ManyToManyField(Car, through='PossessedCar')

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class PossessedCar(models.Model):
    car = models.ForeignKey(Car)
    belongs_to = models.ForeignKey(Person)

    def __str__(self):
        return self.color
