from django.db import IntegrityError, connection
from django.db.models import F, GeneratedField
from django.db.models.functions import Lower
from django.test import TestCase, skipUnlessDBFeature

from .models import (
    GeneratedModel,
    GeneratedModelNotNull,
    GeneratedModelNull,
    GeneratedModelParams,
    GeneratedModelVirtual,
    GeneratedModeOutputField,
)


@skipUnlessDBFeature("supports_generated_columns")
class GeneratedFieldTests(TestCase):
    def _refresh_if_needed(self, m):
        # If the DB doesn't support `INSERT...RETURNING`, the model
        # must be re-fetched from the database for the computed field
        # to be set.
        if connection.features.can_return_columns_from_insert:
            return m
        else:
            return m.__class__.objects.get(id=m.id)

    def test_create(self):
        m = GeneratedModel.objects.create(a=1, b=2)
        m = self._refresh_if_needed(m)
        self.assertEqual(m.field, 3)

    def test_save(self):
        m = GeneratedModel(a=2, b=4)
        m.save()
        self.assertEqual(
            m.field, 6 if connection.features.can_return_columns_from_insert else None
        )
        m = self._refresh_if_needed(m)
        self.assertEqual(m.field, 6)

    def test_bulk_create(self):
        (m,) = GeneratedModel.objects.bulk_create([GeneratedModel(a=3, b=4)])
        self.assertEqual(
            m.field, 7 if connection.features.can_return_columns_from_insert else None
        )

    def test_update(self):
        m = GeneratedModel.objects.create(a=1, b=2)
        GeneratedModel.objects.update(b=3)
        m = GeneratedModel.objects.get(id=m.id)
        self.assertEqual(m.field, 4)

    def test_bulk_update(self):
        m = GeneratedModel.objects.create(a=1, b=2)
        m.a = 3
        GeneratedModel.objects.bulk_update([m], fields=["a"])
        m = GeneratedModel.objects.get(id=m.id)
        self.assertEqual(m.field, 5)

    @skipUnlessDBFeature("supports_generated_columns_params")
    def test_model_with_params(self):
        m = GeneratedModelParams.objects.create()
        m = self._refresh_if_needed(m)
        self.assertEqual(m.field, "Constant")

    @skipUnlessDBFeature("supports_virtual_generated_columns")
    def test_create_virtual(self):
        m = GeneratedModelVirtual.objects.create(name="Test")
        m = self._refresh_if_needed(m)
        self.assertEqual(m.lower_name, "test")

    def test_output_field(self):
        collation = connection.features.test_collations.get("non_default")
        if not collation:
            self.skipTest("Language collations are not supported.")

        m = GeneratedModeOutputField.objects.create(name="NAME")
        field = m._meta.get_field("lower_name")
        db_parameters = field.db_parameters(connection)
        self.assertEqual(db_parameters["collation"], collation)
        self.assertEqual(db_parameters["type"], field.output_field.db_type(connection))
        self.assertNotEqual(
            db_parameters["type"],
            field._resolved_expression.output_field.db_type(connection),
        )

    def test_deconstruct(self):
        *_, desconstruct_kwargs = GeneratedModel._meta.get_field("field").deconstruct()
        self.assertEqual(desconstruct_kwargs, dict(expression=F("a") + F("b")))

    def test_nullable(self):
        m1 = GeneratedModelNull.objects.create(name=None)
        m1 = self._refresh_if_needed(m1)
        self.assertEqual(m1.lower_name, None)
        m2 = GeneratedModelNull.objects.create(name="Name")
        m2 = self._refresh_if_needed(m2)
        self.assertEqual(m2.lower_name, "name")
        with self.assertRaises(IntegrityError):
            GeneratedModelNotNull.objects.create(name=None)

    def test_editable_unsupported(self):
        with self.assertRaises(AssertionError):
            GeneratedField(expression=Lower("name"), editable=False)

    def test_blank_unsupported(self):
        with self.assertRaises(AssertionError):
            GeneratedField(expression=Lower("name"), blank=False)

    def test_default_unsupported(self):
        with self.assertRaises(AssertionError):
            GeneratedField(expression=Lower("name"), default="")
