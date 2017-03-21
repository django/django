from unittest import mock

from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.db import models
from django.test import SimpleTestCase, override_settings
from django.test.utils import isolate_apps


@isolate_apps('contenttypes_tests', attr_name='apps')
class GenericForeignKeyTests(SimpleTestCase):

    def test_missing_content_type_field(self):
        class TaggedItem(models.Model):
            # no content_type field
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey()

        expected = [
            checks.Error(
                "The GenericForeignKey content type references the nonexistent "
                "field 'TaggedItem.content_type'.",
                obj=TaggedItem.content_object,
                id='contenttypes.E002',
            )
        ]
        self.assertEqual(TaggedItem.content_object.check(), expected)

    def test_invalid_content_type_field(self):
        class Model(models.Model):
            content_type = models.IntegerField()  # should be ForeignKey
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey('content_type', 'object_id')

        self.assertEqual(Model.content_object.check(), [
            checks.Error(
                "'Model.content_type' is not a ForeignKey.",
                hint=(
                    "GenericForeignKeys must use a ForeignKey to "
                    "'contenttypes.ContentType' as the 'content_type' field."
                ),
                obj=Model.content_object,
                id='contenttypes.E003',
            )
        ])

    def test_content_type_field_pointing_to_wrong_model(self):
        class Model(models.Model):
            content_type = models.ForeignKey('self', models.CASCADE)  # should point to ContentType
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey('content_type', 'object_id')

        self.assertEqual(Model.content_object.check(), [
            checks.Error(
                "'Model.content_type' is not a ForeignKey to 'contenttypes.ContentType'.",
                hint=(
                    "GenericForeignKeys must use a ForeignKey to "
                    "'contenttypes.ContentType' as the 'content_type' field."
                ),
                obj=Model.content_object,
                id='contenttypes.E004',
            )
        ])

    def test_missing_object_id_field(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType, models.CASCADE)
            # missing object_id field
            content_object = GenericForeignKey()

        self.assertEqual(TaggedItem.content_object.check(), [
            checks.Error(
                "The GenericForeignKey object ID references the nonexistent "
                "field 'object_id'.",
                obj=TaggedItem.content_object,
                id='contenttypes.E001',
            )
        ])

    def test_field_name_ending_with_underscore(self):
        class Model(models.Model):
            content_type = models.ForeignKey(ContentType, models.CASCADE)
            object_id = models.PositiveIntegerField()
            content_object_ = GenericForeignKey('content_type', 'object_id')

        self.assertEqual(Model.content_object_.check(), [
            checks.Error(
                'Field names must not end with an underscore.',
                obj=Model.content_object_,
                id='fields.E001',
            )
        ])

    @override_settings(INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes', 'contenttypes_tests'])
    def test_generic_foreign_key_checks_are_performed(self):
        class Model(models.Model):
            content_object = GenericForeignKey()

        with mock.patch.object(GenericForeignKey, 'check') as check:
            checks.run_checks(app_configs=self.apps.get_app_configs())
        check.assert_called_once_with()


@isolate_apps('contenttypes_tests')
class GenericRelationTests(SimpleTestCase):

    def test_valid_generic_relationship(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType, models.CASCADE)
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey()

        class Bookmark(models.Model):
            tags = GenericRelation('TaggedItem')

        self.assertEqual(Bookmark.tags.field.check(), [])

    def test_valid_generic_relationship_with_explicit_fields(self):
        class TaggedItem(models.Model):
            custom_content_type = models.ForeignKey(ContentType, models.CASCADE)
            custom_object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey('custom_content_type', 'custom_object_id')

        class Bookmark(models.Model):
            tags = GenericRelation(
                'TaggedItem',
                content_type_field='custom_content_type',
                object_id_field='custom_object_id',
            )

        self.assertEqual(Bookmark.tags.field.check(), [])

    def test_pointing_to_missing_model(self):
        class Model(models.Model):
            rel = GenericRelation('MissingModel')

        self.assertEqual(Model.rel.field.check(), [
            checks.Error(
                "Field defines a relation with model 'MissingModel', "
                "which is either not installed, or is abstract.",
                obj=Model.rel.field,
                id='fields.E300',
            )
        ])

    def test_valid_self_referential_generic_relationship(self):
        class Model(models.Model):
            rel = GenericRelation('Model')
            content_type = models.ForeignKey(ContentType, models.CASCADE)
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey('content_type', 'object_id')

        self.assertEqual(Model.rel.field.check(), [])

    def test_missing_generic_foreign_key(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType, models.CASCADE)
            object_id = models.PositiveIntegerField()

        class Bookmark(models.Model):
            tags = GenericRelation('TaggedItem')

        self.assertEqual(Bookmark.tags.field.check(), [
            checks.Error(
                "The GenericRelation defines a relation with the model "
                "'contenttypes_tests.TaggedItem', but that model does not have a "
                "GenericForeignKey.",
                obj=Bookmark.tags.field,
                id='contenttypes.E004',
            )
        ])

    @override_settings(TEST_SWAPPED_MODEL='contenttypes_tests.Replacement')
    def test_pointing_to_swapped_model(self):
        class Replacement(models.Model):
            pass

        class SwappedModel(models.Model):
            content_type = models.ForeignKey(ContentType, models.CASCADE)
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey()

            class Meta:
                swappable = 'TEST_SWAPPED_MODEL'

        class Model(models.Model):
            rel = GenericRelation('SwappedModel')

        self.assertEqual(Model.rel.field.check(), [
            checks.Error(
                "Field defines a relation with the model "
                "'contenttypes_tests.SwappedModel', "
                "which has been swapped out.",
                hint="Update the relation to point at 'settings.TEST_SWAPPED_MODEL'.",
                obj=Model.rel.field,
                id='fields.E301',
            )
        ])

    def test_field_name_ending_with_underscore(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType, models.CASCADE)
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey()

        class InvalidBookmark(models.Model):
            tags_ = GenericRelation('TaggedItem')

        self.assertEqual(InvalidBookmark.tags_.field.check(), [
            checks.Error(
                'Field names must not end with an underscore.',
                obj=InvalidBookmark.tags_.field,
                id='fields.E001',
            )
        ])
