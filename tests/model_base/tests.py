from __future__ import unicode_literals

import unittest

from django.apps.registry import Apps
from django.db import models
from django.test import SimpleTestCase
from django.utils import six


class CustomModelBase(models.base.ModelBase):
    pass


class ModelBaseTests(SimpleTestCase):
    def test_custom_model_base(self):
        test_apps = Apps()

        class CustomBaseModel(six.with_metaclass(CustomModelBase, models.Model)):
            class Meta:
                apps = test_apps

        self.assertIsInstance(CustomBaseModel, CustomModelBase)

    @unittest.skipUnless(six.PY2, 'The __metaclass__ attribute is only considered on Python 2')
    def test_custom_model_base_metaclass(self):
        test_apps = Apps()

        class CustomBaseModel(models.Model):
            __metaclass__ = CustomModelBase

            class Meta:
                apps = test_apps

        self.assertIsInstance(CustomBaseModel, CustomModelBase)
