from django.db import models

class Restaurant(models.Model):
    name = models.CharField(max_length=50)

class Address(models.Model):
    street = models.CharField(max_length=50)
