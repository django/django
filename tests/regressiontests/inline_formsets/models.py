# coding: utf-8
from django.db import models


class School(models.Model):
    name = models.CharField(max_length=100)

class Parent(models.Model):
    name = models.CharField(max_length=100)

class Child(models.Model):
    mother = models.ForeignKey(Parent, related_name='mothers_children')
    father = models.ForeignKey(Parent, related_name='fathers_children')
    school = models.ForeignKey(School)
    name = models.CharField(max_length=100)

class Poet(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class Poem(models.Model):
    poet = models.ForeignKey(Poet)
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name
