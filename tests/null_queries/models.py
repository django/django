from django.db import models


class Poll(models.Model):
    question = models.CharField(max_length=200)


class Choice(models.Model):
    poll = models.ForeignKey(Poll, models.CASCADE)
    choice = models.CharField(max_length=200)

# A set of models with an inner one pointing to two outer ones.


class OuterA(models.Model):
    pass


class OuterB(models.Model):
    data = models.CharField(max_length=10)


class Inner(models.Model):
    first = models.ForeignKey(OuterA, models.CASCADE)
    # second would clash with the __second lookup.
    third = models.ForeignKey(OuterB, models.SET_NULL, null=True)
