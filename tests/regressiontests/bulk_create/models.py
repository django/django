from django.db import models


class Country(models.Model):
    name = models.CharField(max_length=255)
    iso_two_letter = models.CharField(max_length=2)

class Place(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        abstract = True

class Restaurant(Place):
    pass

class Pizzeria(Restaurant):
    pass

class State(models.Model):
    two_letter_code = models.CharField(max_length=2, primary_key=True)