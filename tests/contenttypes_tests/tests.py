# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.db import models
from django.db.models.loading import cache
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.encoding import force_str

from .models import Author, Article


class ContentTypesViewsTests(TestCase):
    fixtures = ['testdata.json']
    urls = 'contenttypes_tests.urls'

    def test_shortcut_with_absolute_url(self):
        "Can view a shortcut for an Author object that has a get_absolute_url method"
        for obj in Author.objects.all():
            short_url = '/shortcut/%s/%s/' % (ContentType.objects.get_for_model(Author).id, obj.pk)
            response = self.client.get(short_url)
            self.assertRedirects(response, 'http://testserver%s' % obj.get_absolute_url(),
                                 status_code=302, target_status_code=404)

    def test_shortcut_no_absolute_url(self):
        "Shortcuts for an object that has no get_absolute_url method raises 404"
        for obj in Article.objects.all():
            short_url = '/shortcut/%s/%s/' % (ContentType.objects.get_for_model(Article).id, obj.pk)
            response = self.client.get(short_url)
            self.assertEqual(response.status_code, 404)

    def test_wrong_type_pk(self):
        short_url = '/shortcut/%s/%s/' % (ContentType.objects.get_for_model(Author).id, 'nobody/expects')
        response = self.client.get(short_url)
        self.assertEqual(response.status_code, 404)

    def test_shortcut_bad_pk(self):
        short_url = '/shortcut/%s/%s/' % (ContentType.objects.get_for_model(Author).id, '42424242')
        response = self.client.get(short_url)
        self.assertEqual(response.status_code, 404)

    def test_nonint_content_type(self):
        an_author = Author.objects.all()[0]
        short_url = '/shortcut/%s/%s/' % ('spam', an_author.pk)
        response = self.client.get(short_url)
        self.assertEqual(response.status_code, 404)

    def test_bad_content_type(self):
        an_author = Author.objects.all()[0]
        short_url = '/shortcut/%s/%s/' % (42424242, an_author.pk)
        response = self.client.get(short_url)
        self.assertEqual(response.status_code, 404)


class IsolatedModelsTestCase(TestCase):

    def setUp(self):
        # If you create a model in a test, the model is accessible in other
        # tests. To avoid this, we need to mock list of all models created in
        # `contenttypes_tests` module.
        self._old_app_models_cache = cache.app_models['contenttypes_tests']
        cache.app_models['contenttypes_tests'] = {}
        self._old_models_cache = cache._get_models_cache
        cache._get_models_cache = {}

    def tearDown(self):
        cache.app_models['contenttypes_tests'] = self._old_app_models_cache
        cache._get_models_cache = self._old_models_cache


class GenericForeignKeyTests(IsolatedModelsTestCase):

    def test_str(self):
        class Model(models.Model):
            field = generic.GenericForeignKey()
        expected = "contenttypes_tests.Model.field"
        actual = force_str(Model.field)
        self.assertEqual(expected, actual)

    def test_missing_content_type_field(self):
        class TaggedItem(models.Model):
            # no content_type field
            object_id = models.PositiveIntegerField()
            content_object = generic.GenericForeignKey()

        errors = TaggedItem.content_object.check()
        expected = [
            checks.Error(
                'The field refers to "content_type" field which is missing.',
                hint=None,
                obj=TaggedItem.content_object,
            )
        ]
        self.assertEqual(errors, expected)

    def test_invalid_content_type_field(self):
        class Model(models.Model):
            content_type = models.IntegerField()  # should be ForeignKey
            object_id = models.PositiveIntegerField()
            content_object = generic.GenericForeignKey(
                'content_type', 'object_id')

        errors = Model.content_object.check()
        expected = [
            checks.Error(
                '"content_type" field is used by a GenericForeignKey '
                    'as content type field and therefore it must be '
                    'a ForeignKey.',
                hint=None,
                obj=Model.content_object,
            )
        ]
        self.assertEqual(errors, expected)

    def test_content_type_field_pointing_to_wrong_model(self):
        class Model(models.Model):
            content_type = models.ForeignKey('self')  # should point to ContentType
            object_id = models.PositiveIntegerField()
            content_object = generic.GenericForeignKey(
                'content_type', 'object_id')

        errors = Model.content_object.check()
        expected = [
            checks.Error(
                '"content_type" field is used by a GenericForeignKey'
                    'as content type field and therefore it must be '
                    'a ForeignKey to ContentType.',
                hint=None,
                obj=Model.content_object,
            )
        ]
        self.assertEqual(errors, expected)

    def test_missing_object_id_field(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType)
            # missing object_id field
            content_object = generic.GenericForeignKey()

        errors = TaggedItem.content_object.check()
        expected = [
            checks.Error(
                'The field refers to "object_id" field which is missing.',
                hint=None,
                obj=TaggedItem.content_object,
            )
        ]
        self.assertEqual(errors, expected)

    def test_field_name_ending_with_underscore(self):
        class Model(models.Model):
            content_type = models.ForeignKey(ContentType)
            object_id = models.PositiveIntegerField()
            content_object_ = generic.GenericForeignKey(
                'content_type', 'object_id')

        errors = Model.content_object_.check()
        expected = [
            checks.Error(
                'Field names must not end with underscores.',
                hint=None,
                obj=Model.content_object_,
            )
        ]
        self.assertEqual(errors, expected)

    def test_generic_foreign_key_checks_are_performed(self):
        class MyGenericForeignKey(generic.GenericForeignKey):
            def check(self, **kwargs):
                return ['performed!']

        class Model(models.Model):
            content_object = MyGenericForeignKey()

        errors = checks.run_checks()
        self.assertEqual(errors, ['performed!'])

    def test_accessor_clash(self):
        class MyModel(models.Model):
            content_type = models.ForeignKey(ContentType)
            object_id = models.PositiveIntegerField()
            content_object = generic.GenericForeignKey()

        class AnotherModel(models.Model):
            rel = models.ForeignKey('MyModel', related_name='content_object')

        errors = checks.run_checks()
        expected = [
            checks.Error(
                'Accessor for field AnotherModel.rel clashes with '
                    'field MyModel.content_object.',
                hint='Rename field MyModel.content_object or add/change '
                    'a related_name argument to the definition '
                    'for field AnotherModel.rel.',
                obj=AnotherModel.rel.field,
            )
        ]
        self.assertEqual(errors, expected)

class GenericRelationshipTests(IsolatedModelsTestCase):

    def test_valid_generic_relationship(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType)
            object_id = models.PositiveIntegerField()
            content_object = generic.GenericForeignKey()

        class Bookmark(models.Model):
            tags = generic.GenericRelation('TaggedItem')

        errors = checks.run_checks()
        self.assertEqual(errors, [])

    def test_valid_generic_relationship_with_explicit_fields(self):
        class TaggedItem(models.Model):
            custom_content_type = models.ForeignKey(ContentType)
            custom_object_id = models.PositiveIntegerField()
            content_object = generic.GenericForeignKey(
                'custom_content_type', 'custom_object_id')

        class Bookmark(models.Model):
            tags = generic.GenericRelation('TaggedItem',
                content_type_field='custom_content_type',
                object_id_field='custom_object_id')

        errors = checks.run_checks()
        self.assertEqual(errors, [])

    def test_pointing_to_missing_model(self):
        class Model(models.Model):
            rel = generic.GenericRelation('MissingModel')

        errors = Model.rel.field.check()
        expected = [
            checks.Error(
                'The field has a relation with model MissingModel, '
                    'which has either not been installed or is abstract.',
                hint='Ensure that you did not misspell the model name and '
                    'the model is not abstract. Does your INSTALLED_APPS '
                    'setting contain the app where MissingModel is defined?',
                obj=Model.rel.field,
            )
        ]
        self.assertEqual(errors, expected)

    def test_valid_self_referential_generic_relationship(self):
        class Model(models.Model):
            rel = generic.GenericRelation('Model')
            content_type = models.ForeignKey(ContentType)
            object_id = models.PositiveIntegerField()
            content_object = generic.GenericForeignKey(
                'content_type', 'object_id')

        errors = Model.rel.field.check()
        self.assertEqual(errors, [])

    def test_missing_content_type_field(self):
        class TaggedItem(models.Model):
            # no content_type field
            object_id = models.PositiveIntegerField()
            content_object = generic.GenericForeignKey()

        class Bookmark(models.Model):
            tags = generic.GenericRelation('TaggedItem')

        errors = checks.run_checks()
        #errors = Bookmark.check()
        expected = [
            checks.Error(
                'The field refers to TaggedItem.content_type field which is missing.',
                hint=None,
                obj=Bookmark.tags.field,
            )
        ]
        self.assertEqual(errors, expected)

    def test_missing_object_id_field(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType)
            # missing object_id field
            content_object = generic.GenericForeignKey()

        class Bookmark(models.Model):
            tags = generic.GenericRelation('TaggedItem')

        errors = checks.run_checks()
        expected = [
            checks.Error(
                'The field refers to TaggedItem.object_id field which is missing.',
                hint=None,
                obj=Bookmark.tags.field,
            )
        ]
        self.assertEqual(errors, expected)

    def test_missing_generic_foreign_key(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType)
            object_id = models.PositiveIntegerField()

        class Bookmark(models.Model):
            tags = generic.GenericRelation('TaggedItem')

        errors = checks.run_checks()
        self.assertEqual(errors, [])

    @override_settings(TEST_SWAPPED_MODEL='contenttypes_tests.Replacement')
    def test_pointing_to_swapped_model(self):
        class Replacement(models.Model):
            pass

        class SwappedModel(models.Model):
            content_type = models.ForeignKey(ContentType)
            object_id = models.PositiveIntegerField()
            content_object = generic.GenericForeignKey()

            class Meta:
                swappable = 'TEST_SWAPPED_MODEL'

        class Model(models.Model):
            rel = generic.GenericRelation('SwappedModel')

        errors = Model.rel.field.check()
        expected = [
            checks.Error(
                'The field defines a relation with the model '
                    'contenttypes_tests.SwappedModel, '
                    'which has been swapped out.',
                hint='Update the relation to point at settings.TEST_SWAPPED_MODEL',
                obj=Model.rel.field,
            )
        ]
        self.assertEqual(errors, expected)

    def test_field_name_ending_with_underscore(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType)
            object_id = models.PositiveIntegerField()
            content_object = generic.GenericForeignKey()

        class InvalidBookmark(models.Model):
            tags_ = generic.GenericRelation('TaggedItem')

        errors = InvalidBookmark.check()
        expected = [
            checks.Error(
                'Fields names must not end with underscores.',
                hint=None,
                obj=InvalidBookmark.tags_.field,
            )
        ]
        self.assertEqual(errors, expected)
