from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Tag(models.Model):
    name = models.CharField(max_length=10)
    parent = models.ForeignKey(
        'self',
        models.SET_NULL,
        blank=True,
        null=True,
        related_name='children',
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Celebrity(models.Model):
    name = models.CharField("Name", max_length=20)
    greatest_fan = models.ForeignKey(
        "Fan",
        models.SET_NULL,
        null=True,
        unique=True,
    )

    def __str__(self):
        return self.name


class Fan(models.Model):
    fan_of = models.ForeignKey(Celebrity, models.CASCADE)


@python_2_unicode_compatible
class Staff(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=50)
    organisation = models.CharField(max_length=100)
    tags = models.ManyToManyField(Tag, through='StaffTag')
    coworkers = models.ManyToManyField('self')

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class StaffTag(models.Model):
    staff = models.ForeignKey(Staff, models.CASCADE)
    tag = models.ForeignKey(Tag, models.CASCADE)

    def __str__(self):
        return "%s -> %s" % (self.tag, self.staff)
