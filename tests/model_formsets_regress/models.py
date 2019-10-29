from django.db import models


class User(models.Model):
    username = models.CharField(max_length=12, unique=True)
    serial = models.IntegerField()


class UserSite(models.Model):
    user = models.ForeignKey(User, models.CASCADE, to_field="username")
    data = models.IntegerField()


class UserProfile(models.Model):
    user = models.ForeignKey(User, models.CASCADE, unique=True, to_field="username")
    about = models.TextField()


class UserPreferences(models.Model):
    user = models.OneToOneField(
        User, models.CASCADE,
        to_field='username',
        primary_key=True,
    )
    favorite_number = models.IntegerField()


class ProfileNetwork(models.Model):
    profile = models.ForeignKey(UserProfile, models.CASCADE, to_field="user")
    network = models.IntegerField()
    identifier = models.IntegerField()


class Place(models.Model):
    name = models.CharField(max_length=50)


class Restaurant(Place):
    pass


class Manager(models.Model):
    restaurant = models.ForeignKey(Restaurant, models.CASCADE)
    name = models.CharField(max_length=50)


class Network(models.Model):
    name = models.CharField(max_length=15)


class Host(models.Model):
    network = models.ForeignKey(Network, models.CASCADE)
    hostname = models.CharField(max_length=25)

    def __str__(self):
        return self.hostname
