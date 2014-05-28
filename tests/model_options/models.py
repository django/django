from django.db import models
from django.utils.encoding import python_2_unicode_compatible


class Country(models.Model):
    name = models.CharField(max_length=50)


class Person(models.Model):
    name = models.CharField(max_length=10)
    person_country = models.ForeignObject(Country,
        from_fields=['person_country_id'], to_fields=['id'])


@python_2_unicode_compatible
class Musician(models.Model):
    name = models.CharField(max_length=30)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Group(models.Model):
    name = models.CharField(max_length=30)
    members = models.ManyToManyField(Musician)

    def __str__(self):
        return self.name


class Quartet(Group):
    pass


@python_2_unicode_compatible
class OwnedVenue(models.Model):
    name = models.CharField(max_length=30)
    group = models.ForeignKey(Group)

    def __str__(self):
        return self.name
