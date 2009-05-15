from django.db import models

class User(models.Model):
    username = models.CharField(max_length=12, unique=True)
    serial = models.IntegerField()

class UserSite(models.Model):
    user = models.ForeignKey(User, to_field="username")
    data = models.IntegerField()

class Place(models.Model):
    name = models.CharField(max_length=50)

class Restaurant(Place):
    pass

class Manager(models.Model):
    retaurant = models.ForeignKey(Restaurant)
    name = models.CharField(max_length=50)
