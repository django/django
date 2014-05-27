# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from freedom.apps.registry import Apps
from freedom.db import models
from freedom.utils import six
from freedom.utils.encoding import python_2_unicode_compatible


class CustomModelBase(models.base.ModelBase):
    pass


class ModelWithCustomBase(six.with_metaclass(CustomModelBase, models.Model)):
    pass


@python_2_unicode_compatible
class UnicodeModel(models.Model):
    title = models.CharField('ÚÑÍ¢ÓÐÉ', max_length=20, default='“Ðjáñgó”')

    class Meta:
        # Disable auto loading of this model as we load it on our own
        apps = Apps()
        verbose_name = 'úñí©óðé µóðéø'
        verbose_name_plural = 'úñí©óðé µóðéøß'

    def __str__(self):
        return self.title


class Unserializable(object):
    """
    An object that migration doesn't know how to serialize.
    """
    pass


class UnserializableModel(models.Model):
    title = models.CharField(max_length=20, default=Unserializable())

    class Meta:
        # Disable auto loading of this model as we load it on our own
        apps = Apps()
