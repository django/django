from django.db import models

class Parent(models.Model):
    name = models.CharField(max_length=128)

class Child(models.Model):
    parent = models.ForeignKey(Parent, editable=False, null=True)
    name = models.CharField(max_length=30, blank=True)

class Genre(models.Model):
    name = models.CharField(max_length=20)

class Band(models.Model):
    name = models.CharField(max_length=20)
    nr_of_members = models.PositiveIntegerField()
    genres = models.ManyToManyField(Genre)

class Musician(models.Model):
    name = models.CharField(max_length=30)

    def __unicode__(self):
        return self.name

class Group(models.Model):
    name = models.CharField(max_length=30)
    members = models.ManyToManyField(Musician, through='Membership')

    def __unicode__(self):
        return self.name

class Membership(models.Model):
    music = models.ForeignKey(Musician)
    group = models.ForeignKey(Group)
    role = models.CharField(max_length=15)

class Quartet(Group):
    pass

class ChordsMusician(Musician):
    pass

class ChordsBand(models.Model):
    name = models.CharField(max_length=30)
    members = models.ManyToManyField(ChordsMusician, through='Invitation')

class Invitation(models.Model):
    player = models.ForeignKey(ChordsMusician)
    band = models.ForeignKey(ChordsBand)
    instrument = models.CharField(max_length=15)
