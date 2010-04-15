import datetime
from django.db import models
from django.utils.translation import ugettext_lazy as _

class Numbers(object):

    @classmethod
    def get_number(self):
        return 2

class Group(models.Model):
    name = models.CharField(_('name'), max_length=100)

class Event(models.Model):
    group = models.ForeignKey(Group)

class Happening(models.Model):
    when = models.DateTimeField(blank=True, default=datetime.datetime.now)
    name = models.CharField(blank=True, max_length=100, default=lambda:"test")
    number = models.IntegerField(blank=True, default=Numbers.get_number)
