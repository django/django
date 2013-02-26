from __future__ import absolute_import

import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _


def standalone_number(self):
    return 1

class Numbers(object):
    @staticmethod
    def get_static_number(self):
        return 2

    @classmethod
    def get_class_number(self):
        return 3

    def get_member_number(self):
        return 4

nn = Numbers()

class Group(models.Model):
    name = models.CharField(_('name'), max_length=100)

class Event(models.Model):
    group = models.ForeignKey(Group)

class Happening(models.Model):
    when = models.DateTimeField(blank=True, default=datetime.datetime.now)
    name = models.CharField(blank=True, max_length=100, default=lambda:"test")
    number1 = models.IntegerField(blank=True, default=standalone_number)
    number2 = models.IntegerField(blank=True, default=Numbers.get_static_number)
    number3 = models.IntegerField(blank=True, default=Numbers.get_class_number)
    number4 = models.IntegerField(blank=True, default=nn.get_member_number)
