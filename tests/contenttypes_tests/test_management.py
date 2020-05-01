from unittest import mock

from django.apps.registry import Apps, apps
from django.contrib.contenttypes import management as contenttypes_management
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase, modify_settings
from django.test.utils import captured_stdout

from .models import ModelWithNullFKToSite, Post


@modify_settings(INSTALLED_APPS={'append': ['empty_models', 'no_models']})
class RemoveStaleContentTypesTests(TestCase):
    # Speed up tests by avoiding retrieving ContentTypes for all test apps.
    available_apps = [
        'contenttypes_tests',
        'empty_models',
        'no_models',
        'django.contrib.contenttypes',
    ]

    def setUp(self):
        self.before_count = ContentType.objects.count()
        self.content_type = ContentType.objects.create(app_label='contenttypes_tests', model='Fake')
        self.app_config = apps.get_app_config('contenttypes_tests')

    def test_interactive_true_with_dependent_objects(self):
        """
        interactive mode (the default) deletes stale content types and warns of
        dependent objects.
        """
        post = Post.objects.create(title='post', content_type=self.content_type)
        # A related object is needed to show that a custom collector with
        # can_fast_delete=False is needed.
        ModelWithNullFKToSite.objects.create(post=post)
        with mock.patch('builtins.input', return_value='yes'):
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
        interactive mode deletes stale content types even if there aren't any
        dependent objects.
        """
        with mock.patch('builtins.input', return_value='yes'):
            with captured_stdout() as stdout:
                call_command('remove_stale_contenttypes', verbosity=2)
        self.assertIn("Deleting stale content type", stdout.getvalue())
        self.assertEqual(ContentType.objects.count(), self.before_count)

    def test_interactive_false(self):
        """non-interactive mode deletes stale content types."""
        with captured_stdout() as stdout:
            call_command('remove_stale_contenttypes', interactive=False, verbosity=2)
        self.assertIn('Deleting stale content type', stdout.getvalue())
        self.assertEqual(ContentType.objects.count(), self.before_count)

    def test_unavailable_content_type_model(self):
        """A ContentType isn't created if the model isn't available."""
        apps = Apps()
        with self.assertNumQueries(0):
            contenttypes_management.create_contenttypes(self.app_config, interactive=False, verbosity=0, apps=apps)
        self.assertEqual(ContentType.objects.count(), self.before_count + 1)

    @modify_settings(INSTALLED_APPS={'remove': ['empty_models']})
    def test_contenttypes_removed_in_installed_apps_without_models(self):
        ContentType.objects.create(app_label='empty_models', model='Fake 1')
        ContentType.objects.create(app_label='no_models', model='Fake 2')
        with mock.patch('builtins.input', return_value='yes'), captured_stdout() as stdout:
            call_command('remove_stale_contenttypes', verbosity=2)
        self.assertNotIn(
            "Deleting stale content type 'empty_models | Fake 1'",
            stdout.getvalue(),
        )
        self.assertIn(
            "Deleting stale content type 'no_models | Fake 2'",
            stdout.getvalue(),
        )
        self.assertEqual(ContentType.objects.count(), self.before_count + 1)

    @modify_settings(INSTALLED_APPS={'remove': ['empty_models']})
    def test_contenttypes_removed_for_apps_not_in_installed_apps(self):
        ContentType.objects.create(app_label='empty_models', model='Fake 1')
        ContentType.objects.create(app_label='no_models', model='Fake 2')
        with mock.patch('builtins.input', return_value='yes'), captured_stdout() as stdout:
            call_command('remove_stale_contenttypes', include_stale_apps=True, verbosity=2)
        self.assertIn(
            "Deleting stale content type 'empty_models | Fake 1'",
            stdout.getvalue(),
        )
        self.assertIn(
            "Deleting stale content type 'no_models | Fake 2'",
            stdout.getvalue(),
        )
        self.assertEqual(ContentType.objects.count(), self.before_count)
