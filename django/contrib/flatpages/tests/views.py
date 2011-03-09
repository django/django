import os
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.flatpages.models import FlatPage
from django.test import TestCase

class FlatpageViewTests(TestCase):
    fixtures = ['sample_flatpages']
    urls = 'django.contrib.flatpages.tests.urls'

    def setUp(self):
        self.old_MIDDLEWARE_CLASSES = settings.MIDDLEWARE_CLASSES
        flatpage_middleware_class = 'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware'
        if flatpage_middleware_class in settings.MIDDLEWARE_CLASSES:
            settings.MIDDLEWARE_CLASSES = tuple(m for m in settings.MIDDLEWARE_CLASSES if m != flatpage_middleware_class)
        self.old_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (
            os.path.join(
                os.path.dirname(__file__),
                'templates'
            ),
        )
        self.old_LOGIN_URL = settings.LOGIN_URL
        settings.LOGIN_URL = '/accounts/login/'

    def tearDown(self):
        settings.MIDDLEWARE_CLASSES = self.old_MIDDLEWARE_CLASSES
        settings.TEMPLATE_DIRS = self.old_TEMPLATE_DIRS
        settings.LOGIN_URL = self.old_LOGIN_URL

    def test_view_flatpage(self):
        "A flatpage can be served through a view"
        response = self.client.get('/flatpage_root/flatpage/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<p>Isn't it flat!</p>")

    def test_view_non_existent_flatpage(self):
        "A non-existent flatpage raises 404 when served through a view"
        response = self.client.get('/flatpage_root/no_such_flatpage/')
        self.assertEqual(response.status_code, 404)

    def test_view_authenticated_flatpage(self):
        "A flatpage served through a view can require authentication"
        response = self.client.get('/flatpage_root/sekrit/')
        self.assertRedirects(response, '/accounts/login/?next=/flatpage_root/sekrit/')
        User.objects.create_user('testuser', 'test@example.com', 's3krit')
        self.client.login(username='testuser',password='s3krit')
        response = self.client.get('/flatpage_root/sekrit/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<p>Isn't it sekrit!</p>")

    def test_fallback_flatpage(self):
        "A fallback flatpage won't be served if the middleware is disabled"
        response = self.client.get('/flatpage/')
        self.assertEqual(response.status_code, 404)

    def test_fallback_non_existent_flatpage(self):
        "A non-existent flatpage won't be served if the fallback middlware is disabled"
        response = self.client.get('/no_such_flatpage/')
        self.assertEqual(response.status_code, 404)

    def test_view_flatpage_special_chars(self):
        "A flatpage with special chars in the URL can be served through a view"
        fp = FlatPage.objects.create(
            url="/some.very_special~chars-here/",
            title="A very special page",
            content="Isn't it special!",
            enable_comments=False,
            registration_required=False,
        )
        fp.sites.add(settings.SITE_ID)

        response = self.client.get('/flatpage_root/some.very_special~chars-here/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<p>Isn't it special!</p>")
