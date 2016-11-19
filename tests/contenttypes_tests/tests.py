import datetime

from django.apps.registry import Apps, apps
from django.conf import settings
from django.contrib.contenttypes import management as contenttypes_management
from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import checks, management
from django.core.management import call_command
from django.db import connections, migrations, models
from django.test import (
    SimpleTestCase, TestCase, TransactionTestCase, mock, override_settings,
)
from django.test.utils import captured_stdout, isolate_apps
from django.utils.encoding import force_str, force_text

from .models import (
    Article, Author, ModelWithNullFKToSite, Post, SchemeIncludedURL,
    Site as MockSite,
)


@override_settings(ROOT_URLCONF='contenttypes_tests.urls')
class ContentTypesViewsTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # don't use the manager because we want to ensure the site exists
        # with pk=1, regardless of whether or not it already exists.
        cls.site1 = Site(pk=1, domain='testserver', name='testserver')
        cls.site1.save()
        cls.author1 = Author.objects.create(name='Boris')
        cls.article1 = Article.objects.create(
            title='Old Article', slug='old_article', author=cls.author1,
            date_created=datetime.datetime(2001, 1, 1, 21, 22, 23)
        )
        cls.article2 = Article.objects.create(
            title='Current Article', slug='current_article', author=cls.author1,
            date_created=datetime.datetime(2007, 9, 17, 21, 22, 23)
        )
        cls.article3 = Article.objects.create(
            title='Future Article', slug='future_article', author=cls.author1,
            date_created=datetime.datetime(3000, 1, 1, 21, 22, 23)
        )
        cls.scheme1 = SchemeIncludedURL.objects.create(url='http://test_scheme_included_http/')
        cls.scheme2 = SchemeIncludedURL.objects.create(url='https://test_scheme_included_https/')
        cls.scheme3 = SchemeIncludedURL.objects.create(url='//test_default_scheme_kept/')

    def setUp(self):
        Site.objects.clear_cache()

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
        the tested URLs are: "http://...", "https://..." and "//..."
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

    @mock.patch('django.apps.apps.get_model')
    def test_shortcut_view_with_null_site_fk(self, get_model):
        """
        The shortcut view works if a model's ForeignKey to site is None.
        """
        get_model.side_effect = lambda *args, **kwargs: MockSite if args[0] == 'sites.Site' else ModelWithNullFKToSite

        obj = ModelWithNullFKToSite.objects.create(title='title')
        url = '/shortcut/%s/%s/' % (ContentType.objects.get_for_model(ModelWithNullFKToSite).id, obj.pk)
        response = self.client.get(url)
        self.assertRedirects(
            response, '%s' % obj.get_absolute_url(),
            fetch_redirect_response=False,
        )

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


@override_settings(SILENCED_SYSTEM_CHECKS=['fields.W342'])  # ForeignKey(unique=True)
@isolate_apps('contenttypes_tests', attr_name='apps')
class GenericForeignKeyTests(SimpleTestCase):

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
                hint=(
                    "GenericForeignKeys must use a ForeignKey to "
                    "'contenttypes.ContentType' as the 'content_type' field."
                ),
                obj=Model.content_object,
                id='contenttypes.E003',
            )
        ]
        self.assertEqual(errors, expected)

    def test_content_type_field_pointing_to_wrong_model(self):
        class Model(models.Model):
            content_type = models.ForeignKey('self', models.CASCADE)  # should point to ContentType
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey(
                'content_type', 'object_id')

        errors = Model.content_object.check()
        expected = [
            checks.Error(
                "'Model.content_type' is not a ForeignKey to 'contenttypes.ContentType'.",
                hint=(
                    "GenericForeignKeys must use a ForeignKey to "
                    "'contenttypes.ContentType' as the 'content_type' field."
                ),
                obj=Model.content_object,
                id='contenttypes.E004',
            )
        ]
        self.assertEqual(errors, expected)

    def test_missing_object_id_field(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType, models.CASCADE)
            # missing object_id field
            content_object = GenericForeignKey()

        errors = TaggedItem.content_object.check()
        expected = [
            checks.Error(
                "The GenericForeignKey object ID references the non-existent field 'object_id'.",
                obj=TaggedItem.content_object,
                id='contenttypes.E001',
            )
        ]
        self.assertEqual(errors, expected)

    def test_field_name_ending_with_underscore(self):
        class Model(models.Model):
            content_type = models.ForeignKey(ContentType, models.CASCADE)
            object_id = models.PositiveIntegerField()
            content_object_ = GenericForeignKey(
                'content_type', 'object_id')

        errors = Model.content_object_.check()
        expected = [
            checks.Error(
                'Field names must not end with an underscore.',
                obj=Model.content_object_,
                id='fields.E001',
            )
        ]
        self.assertEqual(errors, expected)

    @override_settings(INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes', 'contenttypes_tests'])
    def test_generic_foreign_key_checks_are_performed(self):
        class Model(models.Model):
            content_object = GenericForeignKey()

        with mock.patch.object(GenericForeignKey, 'check') as check:
            checks.run_checks(app_configs=self.apps.get_app_configs())
        check.assert_called_once_with()


@isolate_apps('contenttypes_tests')
class GenericRelationshipTests(SimpleTestCase):

    def test_valid_generic_relationship(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType, models.CASCADE)
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey()

        class Bookmark(models.Model):
            tags = GenericRelation('TaggedItem')

        errors = Bookmark.tags.field.check()
        self.assertEqual(errors, [])

    def test_valid_generic_relationship_with_explicit_fields(self):
        class TaggedItem(models.Model):
            custom_content_type = models.ForeignKey(ContentType, models.CASCADE)
            custom_object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey(
                'custom_content_type', 'custom_object_id')

        class Bookmark(models.Model):
            tags = GenericRelation(
                'TaggedItem',
                content_type_field='custom_content_type',
                object_id_field='custom_object_id',
            )

        errors = Bookmark.tags.field.check()
        self.assertEqual(errors, [])

    def test_pointing_to_missing_model(self):
        class Model(models.Model):
            rel = GenericRelation('MissingModel')

        errors = Model.rel.field.check()
        expected = [
            checks.Error(
                "Field defines a relation with model 'MissingModel', "
                "which is either not installed, or is abstract.",
                obj=Model.rel.field,
                id='fields.E300',
            )
        ]
        self.assertEqual(errors, expected)

    def test_valid_self_referential_generic_relationship(self):
        class Model(models.Model):
            rel = GenericRelation('Model')
            content_type = models.ForeignKey(ContentType, models.CASCADE)
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey(
                'content_type', 'object_id')

        errors = Model.rel.field.check()
        self.assertEqual(errors, [])

    def test_missing_generic_foreign_key(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType, models.CASCADE)
            object_id = models.PositiveIntegerField()

        class Bookmark(models.Model):
            tags = GenericRelation('TaggedItem')

        errors = Bookmark.tags.field.check()
        expected = [
            checks.Error(
                "The GenericRelation defines a relation with the model "
                "'contenttypes_tests.TaggedItem', but that model does not have a "
                "GenericForeignKey.",
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
            content_type = models.ForeignKey(ContentType, models.CASCADE)
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey()

            class Meta:
                swappable = 'TEST_SWAPPED_MODEL'

        class Model(models.Model):
            rel = GenericRelation('SwappedModel')

        errors = Model.rel.field.check()
        expected = [
            checks.Error(
                "Field defines a relation with the model "
                "'contenttypes_tests.SwappedModel', "
                "which has been swapped out.",
                hint="Update the relation to point at 'settings.TEST_SWAPPED_MODEL'.",
                obj=Model.rel.field,
                id='fields.E301',
            )
        ]
        self.assertEqual(errors, expected)

    def test_field_name_ending_with_underscore(self):
        class TaggedItem(models.Model):
            content_type = models.ForeignKey(ContentType, models.CASCADE)
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey()

        class InvalidBookmark(models.Model):
            tags_ = GenericRelation('TaggedItem')

        errors = InvalidBookmark.tags_.field.check()
        expected = [
            checks.Error(
                'Field names must not end with an underscore.',
                obj=InvalidBookmark.tags_.field,
                id='fields.E001',
            )
        ]
        self.assertEqual(errors, expected)


class UpdateContentTypesTests(TestCase):
    def setUp(self):
        self.before_count = ContentType.objects.count()
        self.content_type = ContentType.objects.create(app_label='contenttypes_tests', model='Fake')
        self.app_config = apps.get_app_config('contenttypes_tests')

    def test_interactive_true_with_dependent_objects(self):
        """
        interactive mode of remove_stale_contenttypes (the default) should
        delete stale contenttypes and warn of dependent objects.
        """
        post = Post.objects.create(title='post', content_type=self.content_type)
        # A related object is needed to show that a custom collector with
        # can_fast_delete=False is needed.
        ModelWithNullFKToSite.objects.create(post=post)
        with mock.patch(
            'django.contrib.contenttypes.management.commands.remove_stale_contenttypes.input',
            return_value='yes'
        ):
            with captured_stdout() as stdout:
                call_command('remove_stale_contenttypes', verbosity=2, stdout=stdout)
        self.assertEqual(Post.objects.count(), 0)
        output = stdout.getvalue()
        self.assertIn('- Content type for contenttypes_tests.Fake', output)
        self.assertIn('- 1 contenttypes_tests.Post object(s)', output)
        self.assertIn('- 1 contenttypes_tests.ModelWithNullFKToSite', output)
        self.assertIn('Deleting stale content type', output)
        self.assertEqual(ContentType.objects.count(), self.before_count)

    def test_interactive_true_without_dependent_objects(self):
        """
        interactive mode of remove_stale_contenttypes (the default) should
        delete stale contenttypes even if there aren't any dependent objects.
        """
        with mock.patch(
            'django.contrib.contenttypes.management.commands.remove_stale_contenttypes.input',
            return_value='yes'
        ):
            with captured_stdout() as stdout:
                call_command('remove_stale_contenttypes', verbosity=2)
        self.assertIn("Deleting stale content type", stdout.getvalue())
        self.assertEqual(ContentType.objects.count(), self.before_count)

    def test_interactive_false(self):
        """
        non-interactive mode of remove_stale_contenttypes shouldn't delete
        stale content types.
        """
        with captured_stdout() as stdout:
            call_command('remove_stale_contenttypes', interactive=False, verbosity=2)
        self.assertIn("Stale content types remain.", stdout.getvalue())
        self.assertEqual(ContentType.objects.count(), self.before_count + 1)

    def test_unavailable_content_type_model(self):
        """
        A ContentType shouldn't be created if the model isn't available.
        """
        apps = Apps()
        with self.assertNumQueries(0):
            contenttypes_management.create_contenttypes(self.app_config, interactive=False, verbosity=0, apps=apps)
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
        When using multiple databases, ContentType.objects.get_for_model() uses
        db_for_read().
        """
        ContentType.objects.clear_cache()

        with self.assertNumQueries(0, using='default'), \
                self.assertNumQueries(1, using='other'):
            ContentType.objects.get_for_model(Author)


@override_settings(
    MIGRATION_MODULES=dict(settings.MIGRATION_MODULES, contenttypes_tests='contenttypes_tests.operations_migrations'),
)
class ContentTypeOperationsTests(TransactionTestCase):
    available_apps = [
        'contenttypes_tests',
        'django.contrib.contenttypes',
    ]

    def setUp(self):
        app_config = apps.get_app_config('contenttypes_tests')
        models.signals.post_migrate.connect(self.assertOperationsInjected, sender=app_config)

    def tearDown(self):
        app_config = apps.get_app_config('contenttypes_tests')
        models.signals.post_migrate.disconnect(self.assertOperationsInjected, sender=app_config)

    def assertOperationsInjected(self, plan, **kwargs):
        for migration, _backward in plan:
            operations = iter(migration.operations)
            for operation in operations:
                if isinstance(operation, migrations.RenameModel):
                    next_operation = next(operations)
                    self.assertIsInstance(next_operation, contenttypes_management.RenameContentType)
                    self.assertEqual(next_operation.app_label, migration.app_label)
                    self.assertEqual(next_operation.old_model, operation.old_name_lower)
                    self.assertEqual(next_operation.new_model, operation.new_name_lower)

    def test_existing_content_type_rename(self):
        ContentType.objects.create(app_label='contenttypes_tests', model='foo')
        management.call_command(
            'migrate', 'contenttypes_tests', database='default', interactive=False, verbosity=0,
        )
        self.assertFalse(ContentType.objects.filter(app_label='contenttypes_tests', model='foo').exists())
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='renamedfoo').exists())
        management.call_command(
            'migrate', 'contenttypes_tests', 'zero', database='default', interactive=False, verbosity=0,
        )
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='foo').exists())
        self.assertFalse(ContentType.objects.filter(app_label='contenttypes_tests', model='renamedfoo').exists())

    def test_missing_content_type_rename_ignore(self):
        management.call_command(
            'migrate', 'contenttypes_tests', database='default', interactive=False, verbosity=0,
        )
        self.assertFalse(ContentType.objects.filter(app_label='contenttypes_tests', model='foo').exists())
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='renamedfoo').exists())
        management.call_command(
            'migrate', 'contenttypes_tests', 'zero', database='default', interactive=False, verbosity=0,
        )
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='foo').exists())
        self.assertFalse(ContentType.objects.filter(app_label='contenttypes_tests', model='renamedfoo').exists())

    def test_content_type_rename_conflict(self):
        ContentType.objects.create(app_label='contenttypes_tests', model='foo')
        ContentType.objects.create(app_label='contenttypes_tests', model='renamedfoo')
        management.call_command(
            'migrate', 'contenttypes_tests', database='default', interactive=False, verbosity=0,
        )
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='foo').exists())
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='renamedfoo').exists())
        management.call_command(
            'migrate', 'contenttypes_tests', 'zero', database='default', interactive=False, verbosity=0,
        )
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='foo').exists())
        self.assertTrue(ContentType.objects.filter(app_label='contenttypes_tests', model='renamedfoo').exists())
