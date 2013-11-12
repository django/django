from django.db import models


class Person(models.Model):
    name = models.CharField(max_length=200)


class Movie(models.Model):
    title = models.CharField(max_length=200)
    director = models.ForeignKey(Person)


class Event(models.Model):
    pass


class Screening(Event):
    movie = models.ForeignKey(Movie)


class ScreeningNullFK(Event):
    movie = models.ForeignKey(Movie, null=True)


class Package(models.Model):
    screening = models.ForeignKey(Screening, null=True)


class PackageNullFK(models.Model):
    screening = models.ForeignKey(ScreeningNullFK, null=True)
