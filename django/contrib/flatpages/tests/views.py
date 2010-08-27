import os
from django.conf import settings
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
        settings.DEBUG = True
    def tearDown(self):
        settings.MIDDLEWARE_CLASSES = self.old_MIDDLEWARE_CLASSES
        settings.TEMPLATE_DIRS = self.old_TEMPLATE_DIRS

    def test_view_flatpage(self):
        "A flatpage can be served through a view"
        response = self.client.get('/flatpage_root/flatpage/')
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "<p>Isn't it flat!</p>")

    def test_view_non_existent_flatpage(self):
        "A non-existent flatpage raises 404 when served through a view"
        response = self.client.get('/flatpage_root/no_such_flatpage/')
        self.assertEquals(response.status_code, 404)

    def test_view_authenticated_flatpage(self):
        "A flatpage served through a view can require authentication"
        response = self.client.get('/flatpage_root/sekrit/')
        self.assertRedirects(response, '/accounts/login/?next=/flatpage_root/sekrit/')

    def test_fallback_flatpage(self):
        "A fallback flatpage won't be served if the middleware is disabled"
        response = self.client.get('/flatpage/')
        self.assertEquals(response.status_code, 404)

    def test_fallback_non_existent_flatpage(self):
        "A non-existent flatpage won't be served if the fallback middlware is disabled"
        response = self.client.get('/no_such_flatpage/')
        self.assertEquals(response.status_code, 404)
