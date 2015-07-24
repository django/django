import json
import uuid

from django.core import exceptions, serializers
from django.db import IntegrityError, models
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from .models import (
    NullableUUIDModel, PrimaryKeyUUIDModel, RelatedToUUIDModel, UUIDGrandchild,
    UUIDModel,
)


class TestSaveLoad(TestCase):
    def test_uuid_instance(self):
        instance = UUIDModel.objects.create(field=uuid.uuid4())
        loaded = UUIDModel.objects.get()
        self.assertEqual(loaded.field, instance.field)

    def test_str_instance_no_hyphens(self):
        UUIDModel.objects.create(field='550e8400e29b41d4a716446655440000')
        loaded = UUIDModel.objects.get()
        self.assertEqual(loaded.field, uuid.UUID('550e8400e29b41d4a716446655440000'))

    def test_str_instance_hyphens(self):
        UUIDModel.objects.create(field='550e8400-e29b-41d4-a716-446655440000')
        loaded = UUIDModel.objects.get()
        self.assertEqual(loaded.field, uuid.UUID('550e8400e29b41d4a716446655440000'))

    def test_str_instance_bad_hyphens(self):
        UUIDModel.objects.create(field='550e84-00-e29b-41d4-a716-4-466-55440000')
        loaded = UUIDModel.objects.get()
        self.assertEqual(loaded.field, uuid.UUID('550e8400e29b41d4a716446655440000'))

    def test_null_handling(self):
        NullableUUIDModel.objects.create(field=None)
        loaded = NullableUUIDModel.objects.get()
        self.assertEqual(loaded.field, None)

    def test_wrong_value(self):
        self.assertRaisesMessage(
            ValueError, 'badly formed hexadecimal UUID string',
            UUIDModel.objects.get, field='not-a-uuid')

        self.assertRaisesMessage(
            ValueError, 'badly formed hexadecimal UUID string',
            UUIDModel.objects.create, field='not-a-uuid')


class TestMigrations(TestCase):

    def test_deconstruct(self):
        field = models.UUIDField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(kwargs, {})


class TestQuerying(TestCase):
    def setUp(self):
        self.objs = [
            NullableUUIDModel.objects.create(field=uuid.uuid4()),
            NullableUUIDModel.objects.create(field='550e8400e29b41d4a716446655440000'),
            NullableUUIDModel.objects.create(field=None),
        ]

    def test_exact(self):
        self.assertSequenceEqual(
            NullableUUIDModel.objects.filter(field__exact='550e8400e29b41d4a716446655440000'),
            [self.objs[1]]
        )

    def test_isnull(self):
        self.assertSequenceEqual(
            NullableUUIDModel.objects.filter(field__isnull=True),
            [self.objs[2]]
        )


class TestSerialization(TestCase):
    test_data = '[{"fields": {"field": "550e8400-e29b-41d4-a716-446655440000"}, "model": "model_fields.uuidmodel", "pk": null}]'

    def test_dumping(self):
        instance = UUIDModel(field=uuid.UUID('550e8400e29b41d4a716446655440000'))
        data = serializers.serialize('json', [instance])
        self.assertEqual(json.loads(data), json.loads(self.test_data))

    def test_loading(self):
        instance = list(serializers.deserialize('json', self.test_data))[0].object
        self.assertEqual(instance.field, uuid.UUID('550e8400-e29b-41d4-a716-446655440000'))


class TestValidation(TestCase):
    def test_invalid_uuid(self):
        field = models.UUIDField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('550e8400', None)
        self.assertEqual(cm.exception.code, 'invalid')
        self.assertEqual(cm.exception.message % cm.exception.params, "'550e8400' is not a valid UUID.")

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
        # Check that the two objects were correctly created.
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
        # exercises ForeignKey.get_db_prep_value()
        UUIDGrandchild().save()


class TestAsPrimaryKeyTransactionTests(TransactionTestCase):
    # Need a TransactionTestCase to avoid deferring FK constraint checking.
    available_apps = ['model_fields']

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_unsaved_fk(self):
        u1 = PrimaryKeyUUIDModel()
        with self.assertRaises(IntegrityError):
            RelatedToUUIDModel.objects.create(uuid_fk=u1)
