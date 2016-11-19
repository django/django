from swappable_models.models import Article

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import management
from django.test import TestCase, override_settings
from django.utils.six import StringIO


class SwappableModelTests(TestCase):

    @override_settings(TEST_ARTICLE_MODEL='swappable_models.AlternateArticle')
    def test_generated_data(self):
        "Permissions and content types are not created for a swapped model"

        # Delete all permissions and content_types
        Permission.objects.filter(content_type__app_label='swappable_models').delete()
        ContentType.objects.filter(app_label='swappable_models').delete()

        # Re-run migrate. This will re-build the permissions and content types.
        new_io = StringIO()
        management.call_command('migrate', interactive=False, stdout=new_io)

        # Content types and permissions exist for the swapped model,
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
        "Model names are case insensitive. Model swapping honors this."
        Article.objects.all()
        self.assertIsNone(Article._meta.swapped)
