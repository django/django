from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Building(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class ClassRoom(models.Model):
    room_number = models.IntegerField()
    building = models.ForeignKey(Building)

    def __str__(self):
        return self.room_number


@python_2_unicode_compatible
class BathRoom(models.Model):
    room_number = models.IntegerField()
    building = models.ForeignKey(Building,
                related_name='loo_set', related_query_name='wc')

    def __str__(self):
        return self.room_number


@python_2_unicode_compatible
class Office(models.Model):
    room_number = models.IntegerField()
    building = models.ForeignKey(Building, related_name="offices")

    def __str__(self):
        return self.room_number


@python_2_unicode_compatible
class Cafeteria(models.Model):
    room_number = models.IntegerField()
    building = models.ForeignKey(Building, related_query_name='cafe')

    def __str__(self):
        return self.room_number
