# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps.registry import Apps, apps
from django.contrib.contenttypes import management
from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.db import connections, models
from django.test import TestCase, override_settings
from django.test.utils import captured_stdout
from django.utils.encoding import force_str, force_text

from .models import Article, Author, SchemeIncludedURL


@override_settings(ROOT_URLCONF='contenttypes_tests.urls')
class ContentTypesViewsTests(TestCase):
    fixtures = ['testdata.json']

    def test_shortcut_with_absolute_url(self):
        "Can view a shortcut for an Author object that has a get_absolute_url method"
        for obj in Author.objects.all():
            short_url = '/shortcut/%s/%s/' % (ContentType.objects.get_for_model(Author).id, obj.pk)
            response = self.client.get(short_url)
            self.assertRedirects(response, 'http://testserver%s' % obj.get_absolute_url(),
                                 status_code=302, target_status_code=404)

    def test_shortcut_with_absolute_url_including_scheme(self):
        """
        Can view a shortcut when object's get_absolute_url returns a full URL
        the tested URLs are in fixtures/testdata.json :
        "http://...", "https://..." and "//..."
        """
        for obj in SchemeIncludedURL.objects.all():
            short_url = '/shortcut/%s/%s/' % (ContentType.objects.get_for_model(SchemeIncludedURL).id, obj.pk)
            response = self.client.get(short_url)
            self.assertRedirects(response, obj.get_absolute_url(),
                                 status_code=302,
                                 fetch_redirect_response=False)

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

    def test_create_contenttype_on_the_spot(self):
        """
        Make sure ContentTypeManager.get_for_model creates the corresponding
        content type if it doesn't exist in the database (for some reason).
        """

        class ModelCreatedOnTheFly(models.Model):
            name = models.CharField()

            class Meta:
                verbose_name = 'a model created on the fly'
                app_label = 'my_great_app'
                apps = Apps()

        ct = ContentType.objects.get_for_model(ModelCreatedOnTheFly)
        self.assertEqual(ct.app_label, 'my_great_app')
        self.assertEqual(ct.model, 'modelcreatedonthefly')
        self.assertEqual(force_text(ct), 'modelcreatedonthefly')


class IsolatedModelsTestCase(TestCase):
    def setUp(self):
        # The unmanaged models need to be removed after the test in order to
        # prevent bad interactions with the flush operation in other tests.
        self._old_models = apps.app_configs['contenttypes_tests'].models.copy()

    def tearDown(self):
        apps.app_configs['contenttypes_tests'].models = self._old_models
        apps.all_models['contenttypes_tests'] = self._old_models
        apps.clear_cache()


@override_settings(SILENCED_SYSTEM_CHECKS=['fields.W342'])  # ForeignKey(unique=True)
class GenericForeignKeyTests(IsolatedModelsTestCase):

    def test_str(self):
        class Model(models.Model):
            field = GenericForeignKey()
        expected = "contenttypes_tests.Model.field"
        actual = force_str(Model.field)
        self.assertEqual(expected, actual)

    def test_missing_content_type_field(self):
        class TaggedItem(models.Model):
            # no content_type field
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey()

        errors = TaggedItem.content_object.check()
        expected = [
            checks.Error(
                "The GenericForeignKey content type references the non-existent field 'TaggedItem.content_type'.",
                hint=None,
                obj=TaggedItem.content_object,
                id='contenttypes.E002',
            )
        ]
        self.assertEqual(errors, expected)

    def test_invalid_content_type_field(self):
        class Model(models.Model):
            content_type = models.IntegerField()  # should be ForeignKey
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey(
                'content_type', 'object_id')

        errors = Model.content_object.check()
        expected = [
            checks.Error(
                "'Model.content_type' is not a ForeignKey.",
                hint="GenericForeignKeys must use a ForeignKey to 'contenttypes.ContentType' as the 'content_type' field.",
                obj=Model.content_object,
                id='contenttypes.E003',
            )
        ]
        self.assertEqual(errors, expected)

    def test_content_type_field_pointing_to_wrong_model(self):
        class Model(models.Model):
            content_type = models.ForeignKey('self')  # should point to ContentType
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey(
                'content_type', 'object_id')

        errors = Model.content_object.check()
        expected = [
            checks.Error(
                "'Model.content_type' is not a ForeignKey to 'contenttypes.ContentType'.",
                hint="GenericForeignKeys must use a ForeignKey to 'contenttypes.ContentType' as the 'content_type' field.",
                obj=Model.content_object,
                id='contenttypes.E004',
            )
        ]
        self.assertEqual(errors, expected)

    def test_missing_object_id_field(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType)
            # missing object_id field
            content_object = GenericForeignKey()

        errors = TaggedItem.content_object.check()
        expected = [
            checks.Error(
                "The GenericForeignKey object ID references the non-existent field 'object_id'.",
                hint=None,
                obj=TaggedItem.content_object,
                id='contenttypes.E001',
            )
        ]
        self.assertEqual(errors, expected)

    def test_field_name_ending_with_underscore(self):
        class Model(models.Model):
            content_type = models.ForeignKey(ContentType)
            object_id = models.PositiveIntegerField()
            content_object_ = GenericForeignKey(
                'content_type', 'object_id')

        errors = Model.content_object_.check()
        expected = [
            checks.Error(
                'Field names must not end with an underscore.',
                hint=None,
                obj=Model.content_object_,
                id='fields.E001',
            )
        ]
        self.assertEqual(errors, expected)

    @override_settings(INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes', 'contenttypes_tests'])
    def test_generic_foreign_key_checks_are_performed(self):
        class MyGenericForeignKey(GenericForeignKey):
            def check(self, **kwargs):
                return ['performed!']

        class Model(models.Model):
            content_object = MyGenericForeignKey()

        errors = checks.run_checks()
        self.assertEqual(errors, ['performed!'])


class GenericRelationshipTests(IsolatedModelsTestCase):

    def test_valid_generic_relationship(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType)
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey()

        class Bookmark(models.Model):
            tags = GenericRelation('TaggedItem')

        errors = Bookmark.tags.field.check()
        self.assertEqual(errors, [])

    def test_valid_generic_relationship_with_explicit_fields(self):
        class TaggedItem(models.Model):
            custom_content_type = models.ForeignKey(ContentType)
            custom_object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey(
                'custom_content_type', 'custom_object_id')

        class Bookmark(models.Model):
            tags = GenericRelation('TaggedItem',
                content_type_field='custom_content_type',
                object_id_field='custom_object_id')

        errors = Bookmark.tags.field.check()
        self.assertEqual(errors, [])

    def test_pointing_to_missing_model(self):
        class Model(models.Model):
            rel = GenericRelation('MissingModel')

        errors = Model.rel.field.check()
        expected = [
            checks.Error(
                ("Field defines a relation with model 'MissingModel', "
                 "which is either not installed, or is abstract."),
                hint=None,
                obj=Model.rel.field,
                id='fields.E300',
            )
        ]
        self.assertEqual(errors, expected)

    def test_valid_self_referential_generic_relationship(self):
        class Model(models.Model):
            rel = GenericRelation('Model')
            content_type = models.ForeignKey(ContentType)
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey(
                'content_type', 'object_id')

        errors = Model.rel.field.check()
        self.assertEqual(errors, [])

    def test_missing_generic_foreign_key(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType)
            object_id = models.PositiveIntegerField()

        class Bookmark(models.Model):
            tags = GenericRelation('TaggedItem')

        errors = Bookmark.tags.field.check()
        expected = [
            checks.Error(
                ("The GenericRelation defines a relation with the model "
                 "'contenttypes_tests.TaggedItem', but that model does not have a "
                 "GenericForeignKey."),
                hint=None,
                obj=Bookmark.tags.field,
                id='contenttypes.E004',
            )
        ]
        self.assertEqual(errors, expected)

    @override_settings(TEST_SWAPPED_MODEL='contenttypes_tests.Replacement')
    def test_pointing_to_swapped_model(self):
        class Replacement(models.Model):
            pass

        class SwappedModel(models.Model):
            content_type = models.ForeignKey(ContentType)
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey()

            class Meta:
                swappable = 'TEST_SWAPPED_MODEL'

        class Model(models.Model):
            rel = GenericRelation('SwappedModel')

        errors = Model.rel.field.check()
        expected = [
            checks.Error(
                ("Field defines a relation with the model "
                 "'contenttypes_tests.SwappedModel', "
                 "which has been swapped out."),
                hint="Update the relation to point at 'settings.TEST_SWAPPED_MODEL'.",
                obj=Model.rel.field,
                id='fields.E301',
            )
        ]
        self.assertEqual(errors, expected)

    def test_field_name_ending_with_underscore(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType)
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey()

        class InvalidBookmark(models.Model):
            tags_ = GenericRelation('TaggedItem')

        errors = InvalidBookmark.tags_.field.check()
        expected = [
            checks.Error(
                'Field names must not end with an underscore.',
                hint=None,
                obj=InvalidBookmark.tags_.field,
                id='fields.E001',
            )
        ]
        self.assertEqual(errors, expected)


class UpdateContentTypesTests(TestCase):
    def setUp(self):
        self.before_count = ContentType.objects.count()
        ContentType.objects.create(app_label='contenttypes_tests', model='Fake')
        self.app_config = apps.get_app_config('contenttypes_tests')

    def test_interactive_true(self):
        """
        interactive mode of update_contenttypes() (the default) should delete
        stale contenttypes.
        """
        management.input = lambda x: force_str("yes")
        with captured_stdout() as stdout:
            management.update_contenttypes(self.app_config)
        self.assertIn("Deleting stale content type", stdout.getvalue())
        self.assertEqual(ContentType.objects.count(), self.before_count)

    def test_interactive_false(self):
        """
        non-interactive mode of update_contenttypes() shouldn't delete stale
        content types.
        """
        with captured_stdout() as stdout:
            management.update_contenttypes(self.app_config, interactive=False)
        self.assertIn("Stale content types remain.", stdout.getvalue())
        self.assertEqual(ContentType.objects.count(), self.before_count + 1)


class TestRouter(object):
    def db_for_read(self, model, **hints):
        return 'other'

    def db_for_write(self, model, **hints):
        return 'default'


@override_settings(DATABASE_ROUTERS=[TestRouter()])
class ContentTypesMultidbTestCase(TestCase):

    def setUp(self):
        # Whenever a test starts executing, only the "default" database is
        # connected. We explicitly connect to the "other" database here. If we
        # don't do it, then it will be implicitly connected later when we query
        # it, but in that case some database backends may automatically perform
        # extra queries upon connecting (notably mysql executes
        # "SET SQL_AUTO_IS_NULL = 0"), which will affect assertNumQueries().
        connections['other'].ensure_connection()

    def test_multidb(self):
        """
        Test that, when using multiple databases, we use the db_for_read (see
        #20401).
        """
        ContentType.objects.clear_cache()

        with self.assertNumQueries(0, using='default'), \
                self.assertNumQueries(1, using='other'):
            ContentType.objects.get_for_model(Author)
