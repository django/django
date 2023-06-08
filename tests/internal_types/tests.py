from django.test import SimpleTestCase

from .models import TestInheritedKeyModel, TestModel


class InternalTypeTests(SimpleTestCase):
    def test_internal_types_for_related_fields(self):
        foreign_key_field = TestModel._meta.get_field("foreign_test")
        many_to_many_field = TestModel._meta.get_field("many_test")
        one_to_one_field = TestModel._meta.get_field("one_test")

        self.assertEqual(foreign_key_field.get_internal_type(), "ForeignKey")
        self.assertEqual(many_to_many_field.get_internal_type(), "ManyToManyField")
        self.assertEqual(one_to_one_field.get_internal_type(), "OneToOneField")

    def test_internal_types_for_related_fields_on_inheritance(self):
        foreign_key_field = TestInheritedKeyModel._meta.get_field("foreign_test")
        many_to_many_field = TestInheritedKeyModel._meta.get_field("many_test")
        one_to_one_field = TestInheritedKeyModel._meta.get_field("one_test")

        self.assertEqual(foreign_key_field.get_internal_type(), "ForeignKey")
        self.assertEqual(many_to_many_field.get_internal_type(), "ManyToManyField")
        self.assertEqual(one_to_one_field.get_internal_type(), "OneToOneField")
