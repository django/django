# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Band(models.Model):
    name = models.CharField(max_length=100)
    bio = models.TextField()
    sign_date = models.DateField()

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class Concert(models.Model):
    main_band = models.ForeignKey(Band, related_name='main_concerts')
    opening_band = models.ForeignKey(Band, related_name='opening_concerts',
        blank=True)
    day = models.CharField(max_length=3, choices=((1, 'Fri'), (2, 'Sat')))
    transport = models.CharField(max_length=100, choices=(
        (1, 'Plane'),
        (2, 'Train'),
        (3, 'Bus')
    ), blank=True)


class ValidationTestModel(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    users = models.ManyToManyField(User)
    state = models.CharField(max_length=2, choices=(("CO", "Colorado"), ("WA", "Washington")))
    is_active = models.BooleanField(default=False)
    pub_date = models.DateTimeField()
    band = models.ForeignKey(Band)
    no = models.IntegerField(verbose_name="Number", blank=True, null=True)  # This field is intentionally 2 characters long. See #16080.

    def decade_published_in(self):
        return self.pub_date.strftime('%Y')[:3] + "0's"


class ValidationTestInlineModel(models.Model):
    parent = models.ForeignKey(ValidationTestModel)
