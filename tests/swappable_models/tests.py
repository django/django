from __future__ import unicode_literals

from swappable_models.models import Article

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import management
from django.test import TestCase, override_settings
from django.utils.six import StringIO


class SwappableModelTests(TestCase):

    available_apps = [
        'swappable_models',
        'django.contrib.auth',
        'django.contrib.contenttypes',
    ]

    @override_settings(TEST_ARTICLE_MODEL='swappable_models.AlternateArticle')
    def test_generated_data(self):
        "Permissions and content types are not created for a swapped model"

        # Delete all permissions and content_types
        Permission.objects.filter(content_type__app_label='swappable_models').delete()
        ContentType.objects.filter(app_label='swappable_models').delete()

        # Re-run migrate. This will re-build the permissions and content types.
        new_io = StringIO()
        management.call_command('migrate', load_initial_data=False, interactive=False, stdout=new_io)

        # Check that content types and permissions exist for the swapped model,
        # but not for the swappable model.
        apps_models = [(p.content_type.app_label, p.content_type.model)
                       for p in Permission.objects.all()]
        self.assertIn(('swappable_models', 'alternatearticle'), apps_models)
        self.assertNotIn(('swappable_models', 'article'), apps_models)

        apps_models = [(ct.app_label, ct.model)
                       for ct in ContentType.objects.all()]
        self.assertIn(('swappable_models', 'alternatearticle'), apps_models)
        self.assertNotIn(('swappable_models', 'article'), apps_models)

    @override_settings(TEST_ARTICLE_MODEL='swappable_models.article')
    def test_case_insensitive(self):
        "Model names are case insensitive. Check that model swapping honors this."
        try:
            Article.objects.all()
        except AttributeError:
            self.fail('Swappable model names should be case insensitive.')

        self.assertIsNone(Article._meta.swapped)
