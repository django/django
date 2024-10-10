from django.core.checks import Warning, model_checks
from django.db import connection, models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps

from .fields import (
    ChildNotOKField,
    ChildOKField,
    CustomDescriptorField,
    CustomTypedField,
    NotOKCustomField,
    OKCustomField,
)


class TestDbType(SimpleTestCase):
    def test_db_parameters_respects_db_type(self):
        f = CustomTypedField()
        self.assertEqual(f.db_parameters(connection)["type"], "custom_field")


class DescriptorClassTest(SimpleTestCase):
    def test_descriptor_class(self):
        class CustomDescriptorModel(models.Model):
            name = CustomDescriptorField(max_length=32)

        m = CustomDescriptorModel()
        self.assertFalse(hasattr(m, "_name_get_count"))
        # The field is set to its default in the model constructor.
        self.assertEqual(m._name_set_count, 1)
        m.name = "foo"
        self.assertFalse(hasattr(m, "_name_get_count"))
        self.assertEqual(m._name_set_count, 2)
        self.assertEqual(m.name, "foo")
        self.assertEqual(m._name_get_count, 1)
        self.assertEqual(m._name_set_count, 2)
        m.name = "bar"
        self.assertEqual(m._name_get_count, 1)
        self.assertEqual(m._name_set_count, 3)
        self.assertEqual(m.name, "bar")
        self.assertEqual(m._name_get_count, 2)
        self.assertEqual(m._name_set_count, 3)


# RemovedInDjango61Warning
@isolate_apps("field_subclassing", attr_name="apps")
class TestFieldTransitionFromContributeToClass(SimpleTestCase):
    def setUp(self):
        class MyModel(models.Model):
            not_ok = NotOKCustomField()
            ok = OKCustomField()
            child_not_ok = ChildNotOKField()
            child_ok = ChildOKField()

        self.model = MyModel
        self.warnings = model_checks.check_deprecated_field_contribute_to_class(
            app_configs=self.apps.get_app_configs()
        )

    def test_warning_field_overrides_contribute_to_class_and_not_set_name(self):
        expected_warnings = [
            Warning(
                "%s.contribute_to_class() is deprecated for field '%s' in "
                "model '%s'." % ("NotOKCustomField", "not_ok", "MyModel"),
                hint="Implement __set_name__() instead.",
                obj=self.model,
                id="models.W048",
            ),
            Warning(
                "%s.contribute_to_class() is deprecated for field '%s' in "
                "model '%s'." % ("ChildNotOKField", "child_not_ok", "MyModel"),
                hint="Implement __set_name__() instead.",
                obj=self.model,
                id="models.W048",
            ),
        ]

        self.assertEqual(len(self.warnings), len(expected_warnings))
        for warning, expected in zip(self.warnings, expected_warnings):
            self.assertEqual(warning.msg, expected.msg)
            self.assertEqual(warning.hint, expected.hint)
            self.assertEqual(warning.id, expected.id)

    def test_override_effects_for_both_set_name_and_contribute_to_cls(self):
        # Check if methods are added correctly.
        self.assertTrue(hasattr(self.model, "get_ok_uppercase"))
        self.assertTrue(hasattr(self.model, "get_not_ok_uppercase"))
        self.assertTrue(hasattr(self.model, "get_child_not_ok_uppercase"))
        self.assertTrue(hasattr(self.model, "get_child_ok_uppercase"))
