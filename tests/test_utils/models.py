from django.db import models


class Car(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Person(models.Model):
    name = models.CharField(max_length=100)
    cars = models.ManyToManyField(Car, through='PossessedCar')

    def __str__(self):
        return self.name


class PossessedCar(models.Model):
    car = models.ForeignKey(Car, models.CASCADE)
    belongs_to = models.ForeignKey(Person, models.CASCADE)
