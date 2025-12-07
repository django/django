from django.db import models


class Part(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
        ordering = ("name",)


class Car(models.Model):
    name = models.CharField(max_length=20)
    default_parts = models.ManyToManyField(Part)
    optional_parts = models.ManyToManyField(Part, related_name="cars_optional")

    class Meta:
        ordering = ("name",)


class SportsCar(Car):
    price = models.IntegerField()


class Person(models.Model):
    name = models.CharField(max_length=20)
    fans = models.ManyToManyField("self", related_name="idols", symmetrical=False)
    friends = models.ManyToManyField("self")

    class Meta:
        ordering = ("name",)
