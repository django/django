from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps


@isolate_apps('contenttypes_tests')
class GenericForeignKeyTests(SimpleTestCase):

    def test_str(self):
        class Model(models.Model):
            field = GenericForeignKey()
        self.assertEqual(str(Model.field), 'contenttypes_tests.Model.field')
