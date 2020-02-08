from django.db import models


class Entity(models.Model):
    pass


class Country(Entity):
    name = models.CharField(max_length=30)


class EUCountry(Country):
    join_date = models.DateField()


class City(models.Model):
    name = models.CharField(max_length=30)
    country = models.ForeignKey(Country, models.CASCADE)


class EUCity(models.Model):
    name = models.CharField(max_length=30)
    country = models.ForeignKey(EUCountry, models.CASCADE)


class Person(models.Model):
    name = models.CharField(max_length=30)
    born = models.ForeignKey(City, models.CASCADE, related_name='+')
    died = models.ForeignKey(City, models.CASCADE, related_name='+')


class PersonProfile(models.Model):
    person = models.OneToOneField(Person, models.CASCADE, related_name='profile')
