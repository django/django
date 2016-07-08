from django.db import models


class Event(models.Model):
    dt = models.DateTimeField()


class MaybeEvent(models.Model):
    dt = models.DateTimeField(blank=True, null=True)


class Session(models.Model):
    name = models.CharField(max_length=20)


class SessionEvent(models.Model):
    dt = models.DateTimeField()
    session = models.ForeignKey(Session, models.CASCADE, related_name='events')


class Timestamp(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


class AllDayEvent(models.Model):
    day = models.DateField()
