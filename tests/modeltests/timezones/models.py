from django.db import models

class Event(models.Model):
    dt = models.DateTimeField()

class Timestamp(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
