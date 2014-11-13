# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class SimpleModel(models.Model):
    field = models.IntegerField()
    manager = models.manager.Manager()
