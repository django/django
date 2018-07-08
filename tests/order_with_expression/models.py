from django.db import models


class Musician(models.Model):
    instrument = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        ordering = [models.F('instrument').asc(nulls_last=True)]


class Album(models.Model):
    artist = models.ForeignKey(Musician, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['artist']


class Song(models.Model):
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['album']
