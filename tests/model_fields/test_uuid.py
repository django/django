import json
import uuid

from django.core import exceptions, serializers
from django.db import connection, models
from django.db.models import CharField, F, Value
from django.db.models.functions import Concat, Repeat
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature

from .models import (
    NullableUUIDModel,
    PrimaryKeyUUIDModel,
    RelatedToUUIDModel,
    UUIDGrandchild,
    UUIDModel,
)


class TestSaveLoad(TestCase):
    def test_uuid_instance(self):
        instance = UUIDModel.objects.create(field=uuid.uuid4())
        loaded = UUIDModel.objects.get()
        self.assertEqual(loaded.field, instance.field)

    def test_str_instance_no_hyphens(self):
        UUIDModel.objects.create(field="550e8400e29b41d4a716446655440000")
        loaded = UUIDModel.objects.get()
        self.assertEqual(loaded.field, uuid.UUID("550e8400e29b41d4a716446655440000"))

    def test_str_instance_hyphens(self):
        UUIDModel.objects.create(field="550e8400-e29b-41d4-a716-446655440000")
        loaded = UUIDModel.objects.get()
        self.assertEqual(loaded.field, uuid.UUID("550e8400e29b41d4a716446655440000"))

    def test_str_instance_bad_hyphens(self):
        UUIDModel.objects.create(field="550e84-00-e29b-41d4-a716-4-466-55440000")
        loaded = UUIDModel.objects.get()
        self.assertEqual(loaded.field, uuid.UUID("550e8400e29b41d4a716446655440000"))

    def test_null_handling(self):
        NullableUUIDModel.objects.create(field=None)
        loaded = NullableUUIDModel.objects.get()
        self.assertIsNone(loaded.field)

    def test_pk_validated(self):
        with self.assertRaisesMessage(
            exceptions.ValidationError, "is not a valid UUID"
        ):
            PrimaryKeyUUIDModel.objects.get(pk={})

        with self.assertRaisesMessage(
            exceptions.ValidationError, "is not a valid UUID"
        ):
            PrimaryKeyUUIDModel.objects.get(pk=[])

    def test_wrong_value(self):
        with self.assertRaisesMessage(
            exceptions.ValidationError, "is not a valid UUID"
        ):
            UUIDModel.objects.get(field="not-a-uuid")

        with self.assertRaisesMessage(
            exceptions.ValidationError, "is not a valid UUID"
        ):
            UUIDModel.objects.create(field="not-a-uuid")


class TestMethods(SimpleTestCase):
    def test_deconstruct(self):
        field = models.UUIDField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(kwargs, {})

    def test_to_python(self):
        self.assertIsNone(models.UUIDField().to_python(None))

    def test_to_python_int_values(self):
        self.assertEqual(
            models.UUIDField().to_python(0),
            uuid.UUID("00000000-0000-0000-0000-000000000000"),
        )
        # Works for integers less than 128 bits.
        self.assertEqual(
            models.UUIDField().to_python((2**128) - 1),
            uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
        )

    def test_to_python_int_too_large(self):
        # Fails for integers larger than 128 bits.
        with self.assertRaises(exceptions.ValidationError):
            models.UUIDField().to_python(2**128)


class TestQuerying(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.objs = [
            NullableUUIDModel.objects.create(
                field=uuid.UUID("25d405be-4895-4d50-9b2e-d6695359ce47"),
            ),
            NullableUUIDModel.objects.create(field="550e8400e29b41d4a716446655440000"),
            NullableUUIDModel.objects.create(field=None),
        ]

    def assertSequenceEqualWithoutHyphens(self, qs, result):
        """
        Backends with a native datatype for UUID don't support fragment lookups
        without hyphens because they store values with them.
        """
        self.assertSequenceEqual(
            qs,
            [] if connection.features.has_native_uuid_field else result,
        )

    def test_exact(self):
        self.assertSequenceEqual(
            NullableUUIDModel.objects.filter(
                field__exact="550e8400e29b41d4a716446655440000"
            ),
            [self.objs[1]],
        )
        self.assertSequenceEqual(
            NullableUUIDModel.objects.filter(
                field__exact="550e8400-e29b-41d4-a716-446655440000"
            ),
            [self.objs[1]],
        )

    def test_iexact(self):
        self.assertSequenceEqualWithoutHyphens(
            NullableUUIDModel.objects.filter(
                field__iexact="550E8400E29B41D4A716446655440000"
            ),
            [self.objs[1]],
        )
        self.assertSequenceEqual(
            NullableUUIDModel.objects.filter(
                field__iexact="550E8400-E29B-41D4-A716-446655440000"
            ),
            [self.objs[1]],
        )

    def test_isnull(self):
        self.assertSequenceEqual(
            NullableUUIDModel.objects.filter(field__isnull=True), [self.objs[2]]
        )

    def test_contains(self):
        self.assertSequenceEqualWithoutHyphens(
            NullableUUIDModel.objects.filter(field__contains="8400e29b"),
            [self.objs[1]],
        )
        self.assertSequenceEqual(
            NullableUUIDModel.objects.filter(field__contains="8400-e29b"),
            [self.objs[1]],
        )

    def test_icontains(self):
        self.assertSequenceEqualWithoutHyphens(
            NullableUUIDModel.objects.filter(field__icontains="8400E29B"),
            [self.objs[1]],
        )
        self.assertSequenceEqual(
            NullableUUIDModel.objects.filter(field__icontains="8400-E29B"),
            [self.objs[1]],
        )

    def test_startswith(self):
        self.assertSequenceEqualWithoutHyphens(
            NullableUUIDModel.objects.filter(field__startswith="550e8400e29b4"),
            [self.objs[1]],
        )
        self.assertSequenceEqual(
            NullableUUIDModel.objects.filter(field__startswith="550e8400-e29b-4"),
            [self.objs[1]],
        )

    def test_istartswith(self):
        self.assertSequenceEqualWithoutHyphens(
            NullableUUIDModel.objects.filter(field__istartswith="550E8400E29B4"),
            [self.objs[1]],
        )
        self.assertSequenceEqual(
            NullableUUIDModel.objects.filter(field__istartswith="550E8400-E29B-4"),
            [self.objs[1]],
        )

    def test_endswith(self):
        self.assertSequenceEqualWithoutHyphens(
            NullableUUIDModel.objects.filter(field__endswith="a716446655440000"),
            [self.objs[1]],
        )
        self.assertSequenceEqual(
            NullableUUIDModel.objects.filter(field__endswith="a716-446655440000"),
            [self.objs[1]],
        )

    def test_iendswith(self):
        self.assertSequenceEqualWithoutHyphens(
            NullableUUIDModel.objects.filter(field__iendswith="A716446655440000"),
            [self.objs[1]],
        )
        self.assertSequenceEqual(
            NullableUUIDModel.objects.filter(field__iendswith="A716-446655440000"),
            [self.objs[1]],
        )

    def test_filter_with_expr(self):
        self.assertSequenceEqualWithoutHyphens(
            NullableUUIDModel.objects.annotate(
                value=Concat(Value("8400"), Value("e29b"), output_field=CharField()),
            ).filter(field__contains=F("value")),
            [self.objs[1]],
        )
        self.assertSequenceEqual(
            NullableUUIDModel.objects.annotate(
                value=Concat(
                    Value("8400"), Value("-"), Value("e29b"), output_field=CharField()
                ),
            ).filter(field__contains=F("value")),
            [self.objs[1]],
        )
        self.assertSequenceEqual(
            NullableUUIDModel.objects.annotate(
                value=Repeat(Value("0"), 4, output_field=CharField()),
            ).filter(field__contains=F("value")),
            [self.objs[1]],
        )


class TestSerialization(SimpleTestCase):
    test_data = (
        '[{"fields": {"field": "550e8400-e29b-41d4-a716-446655440000"}, '
        '"model": "model_fields.uuidmodel", "pk": null}]'
    )
    nullable_test_data = (
        '[{"fields": {"field": null}, '
        '"model": "model_fields.nullableuuidmodel", "pk": null}]'
    )

    def test_dumping(self):
        instance = UUIDModel(field=uuid.UUID("550e8400e29b41d4a716446655440000"))
        data = serializers.serialize("json", [instance])
        self.assertEqual(json.loads(data), json.loads(self.test_data))

    def test_loading(self):
        instance = list(serializers.deserialize("json", self.test_data))[0].object
        self.assertEqual(
            instance.field, uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        )

    def test_nullable_loading(self):
        instance = list(serializers.deserialize("json", self.nullable_test_data))[
            0
        ].object
        self.assertIsNone(instance.field)


class TestValidation(SimpleTestCase):
    def test_invalid_uuid(self):
        field = models.UUIDField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean("550e8400", None)
        self.assertEqual(cm.exception.code, "invalid")
        self.assertEqual(
            cm.exception.message % cm.exception.params,
            "“550e8400” is not a valid UUID.",
        )

    def test_uuid_instance_ok(self):
        field = models.UUIDField()
        field.clean(uuid.uuid4(), None)  # no error


class TestAsPrimaryKey(TestCase):
    def test_creation(self):
        PrimaryKeyUUIDModel.objects.create()
        loaded = PrimaryKeyUUIDModel.objects.get()
        self.assertIsInstance(loaded.pk, uuid.UUID)

    def test_uuid_pk_on_save(self):
        saved = PrimaryKeyUUIDModel.objects.create(id=None)
        loaded = PrimaryKeyUUIDModel.objects.get()
        self.assertIsNotNone(loaded.id, None)
        self.assertEqual(loaded.id, saved.id)

    def test_uuid_pk_on_bulk_create(self):
        u1 = PrimaryKeyUUIDModel()
        u2 = PrimaryKeyUUIDModel(id=None)
        PrimaryKeyUUIDModel.objects.bulk_create([u1, u2])
        # The two objects were correctly created.
        u1_found = PrimaryKeyUUIDModel.objects.filter(id=u1.id).exists()
        u2_found = PrimaryKeyUUIDModel.objects.exclude(id=u1.id).exists()
        self.assertTrue(u1_found)
        self.assertTrue(u2_found)
        self.assertEqual(PrimaryKeyUUIDModel.objects.count(), 2)

    def test_underlying_field(self):
        pk_model = PrimaryKeyUUIDModel.objects.create()
        RelatedToUUIDModel.objects.create(uuid_fk=pk_model)
        related = RelatedToUUIDModel.objects.get()
        self.assertEqual(related.uuid_fk.pk, related.uuid_fk_id)

    def test_update_with_related_model_instance(self):
        # regression for #24611
        u1 = PrimaryKeyUUIDModel.objects.create()
        u2 = PrimaryKeyUUIDModel.objects.create()
        r = RelatedToUUIDModel.objects.create(uuid_fk=u1)
        RelatedToUUIDModel.objects.update(uuid_fk=u2)
        r.refresh_from_db()
        self.assertEqual(r.uuid_fk, u2)

    def test_update_with_related_model_id(self):
        u1 = PrimaryKeyUUIDModel.objects.create()
        u2 = PrimaryKeyUUIDModel.objects.create()
        r = RelatedToUUIDModel.objects.create(uuid_fk=u1)
        RelatedToUUIDModel.objects.update(uuid_fk=u2.pk)
        r.refresh_from_db()
        self.assertEqual(r.uuid_fk, u2)

    def test_two_level_foreign_keys(self):
        gc = UUIDGrandchild()
        # exercises ForeignKey.get_db_prep_value()
        gc.save()
        self.assertIsInstance(gc.uuidchild_ptr_id, uuid.UUID)
        gc.refresh_from_db()
        self.assertIsInstance(gc.uuidchild_ptr_id, uuid.UUID)

    @skipUnlessDBFeature("supports_foreign_keys")
    def test_unsaved_fk(self):
        u1 = PrimaryKeyUUIDModel()
        clone = PrimaryKeyUUIDModel.objects.create()
        clone.pk = None
        msg = (
            "save() prohibited to prevent data loss due to unsaved related "
            "object 'uuid_fk'"
        )
        with self.assertRaisesMessage(ValueError, msg):
            RelatedToUUIDModel.objects.create(uuid_fk=u1)
        with self.assertRaisesMessage(ValueError, msg):
            RelatedToUUIDModel.objects.create(uuid_fk=clone)
