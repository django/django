from django.contrib import databrowse
from django.db import models
from django.test import TestCase
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class SomeModel(models.Model):
    some_field = models.CharField(max_length=50)

    def __str__(self):
        return self.some_field


@python_2_unicode_compatible
class SomeOtherModel(models.Model):
    some_other_field = models.CharField(max_length=50)

    def __str__(self):
        return self.some_other_field


@python_2_unicode_compatible
class YetAnotherModel(models.Model):
    yet_another_field = models.CharField(max_length=50)

    def __str__(self):
        return self.yet_another_field


class DatabrowseTests(TestCase):

    def test_databrowse_register_unregister(self):
        databrowse.site.register(SomeModel)
        self.assertTrue(SomeModel in databrowse.site.registry)
        databrowse.site.register(SomeOtherModel, YetAnotherModel)
        self.assertTrue(SomeOtherModel in databrowse.site.registry)
        self.assertTrue(YetAnotherModel in databrowse.site.registry)

        self.assertRaisesMessage(
            databrowse.sites.AlreadyRegistered,
            'The model SomeModel is already registered',
            databrowse.site.register, SomeModel, SomeOtherModel
        )

        databrowse.site.unregister(SomeOtherModel)
        self.assertFalse(SomeOtherModel in databrowse.site.registry)
        databrowse.site.unregister(SomeModel, YetAnotherModel)
        self.assertFalse(SomeModel in databrowse.site.registry)
        self.assertFalse(YetAnotherModel in databrowse.site.registry)

        self.assertRaisesMessage(
            databrowse.sites.NotRegistered,
            'The model SomeModel is not registered',
            databrowse.site.unregister, SomeModel, SomeOtherModel
        )

        self.assertRaisesMessage(
            databrowse.sites.AlreadyRegistered,
            'The model SomeModel is already registered',
            databrowse.site.register, SomeModel, SomeModel
        )
