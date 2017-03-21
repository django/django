from unittest import mock

from django.apps.registry import Apps, apps
from django.contrib.contenttypes import management as contenttypes_management
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import captured_stdout

from .models import ModelWithNullFKToSite, Post


class UpdateContentTypesTests(TestCase):
    def setUp(self):
        self.before_count = ContentType.objects.count()
        self.content_type = ContentType.objects.create(app_label='contenttypes_tests', model='Fake')
        self.app_config = apps.get_app_config('contenttypes_tests')

    def test_interactive_true_with_dependent_objects(self):
        """
        interactive mode of remove_stale_contenttypes (the default) deletes
        stale contenttypes and warn of dependent objects.
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
        interactive mode of remove_stale_contenttypes (the default) deletes
        stale contenttypes even if there aren't any dependent objects.
        """
        with mock.patch('builtins.input', return_value='yes'):
            with captured_stdout() as stdout:
                call_command('remove_stale_contenttypes', verbosity=2)
        self.assertIn("Deleting stale content type", stdout.getvalue())
        self.assertEqual(ContentType.objects.count(), self.before_count)

    def test_interactive_false(self):
        """
        non-interactive mode of remove_stale_contenttypes doesn't delete
        stale content types.
        """
        with captured_stdout() as stdout:
            call_command('remove_stale_contenttypes', interactive=False, verbosity=2)
        self.assertIn("Stale content types remain.", stdout.getvalue())
        self.assertEqual(ContentType.objects.count(), self.before_count + 1)

    def test_unavailable_content_type_model(self):
        """A ContentType isn't created if the model isn't available."""
        apps = Apps()
        with self.assertNumQueries(0):
            contenttypes_management.create_contenttypes(self.app_config, interactive=False, verbosity=0, apps=apps)
        self.assertEqual(ContentType.objects.count(), self.before_count + 1)
