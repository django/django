from django.db import models
from django.contrib import admin

class Parent(models.Model):
    name = models.CharField(max_length=128)

class Child(models.Model):
    parent = models.ForeignKey(Parent, editable=False)
    name = models.CharField(max_length=30, blank=True)