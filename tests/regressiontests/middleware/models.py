# coding: utf-8
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
