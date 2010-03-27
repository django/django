from django.db import models
from django.utils.translation import ugettext_lazy as _

class Group(models.Model):
    name = models.CharField(_('name'), max_length=100)

class Event(models.Model):
    group = models.ForeignKey(Group)
