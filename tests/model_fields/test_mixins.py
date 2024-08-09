from django.db.models.fields.mixins import FieldCacheMixin
from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango60Warning
from django.utils.functional import cached_property

from .models import Foo


# RemovedInDjango60Warning.
class ExampleOld(FieldCacheMixin):
    def get_cache_name(self):
        return "example"


class Example(FieldCacheMixin):
    @cached_property
    def cache_name(self):
        return "example"


class FieldCacheMixinTests(SimpleTestCase):
    def setUp(self):
        self.instance = Foo()
        self.field = Example()

    # RemovedInDjango60Warning: when the deprecation ends, replace with:
    # def test_cache_name_not_implemented(self):
    #   with self.assertRaises(NotImplementedError):
    #       FieldCacheMixin().cache_name
    def test_get_cache_name_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            FieldCacheMixin().get_cache_name()

    # RemovedInDjango60Warning.
    def test_get_cache_name_deprecated(self):
        msg = "Override ExampleOld.cache_name instead of get_cache_name()."
        with self.assertWarnsMessage(RemovedInDjango60Warning, msg) as ctx:
            result = ExampleOld().cache_name
        self.assertEqual(result, "example")
        self.assertEqual(ctx.filename, __file__)

    def test_cache_name(self):
        result = Example().cache_name
        self.assertEqual(result, "example")

    def test_get_cached_value_missing(self):
        with self.assertRaises(KeyError):
            self.field.get_cached_value(self.instance)

    def test_get_cached_value_default(self):
        default = object()
        result = self.field.get_cached_value(self.instance, default=default)
        self.assertIs(result, default)

    def test_get_cached_value_after_set(self):
        value = object()

        self.field.set_cached_value(self.instance, value)
        result = self.field.get_cached_value(self.instance)

        self.assertIs(result, value)

    def test_is_cached_false(self):
        result = self.field.is_cached(self.instance)
        self.assertFalse(result)

    def test_is_cached_true(self):
        self.field.set_cached_value(self.instance, 1)
        result = self.field.is_cached(self.instance)
        self.assertTrue(result)

    def test_delete_cached_value(self):
        self.field.set_cached_value(self.instance, 1)
        self.field.delete_cached_value(self.instance)
        result = self.field.is_cached(self.instance)
        self.assertFalse(result)
