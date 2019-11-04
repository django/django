from django.db import models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps


@isolate_apps('model_meta')
class TestManagerInheritanceFromFuture(SimpleTestCase):
    def test_defined(self):
        """
        Meta.manager_inheritance_from_future can be defined for backwards
        compatibility with Django 1.11.
        """
        class FuturisticModel(models.Model):
            class Meta:
                manager_inheritance_from_future = True  # No error raised.
