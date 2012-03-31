import os
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.test.utils import override_settings


@override_settings(
    LOGIN_URL='/accounts/login/',
    MIDDLEWARE_CLASSES=(
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    ),
    TEMPLATE_DIRS=(
        os.path.join(os.path.dirname(__file__), 'templates'),
    ),
)
class FlatpageCSRFTests(TestCase):
    fixtures = ['sample_flatpages']
    urls = 'django.contrib.flatpages.tests.urls'

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def test_view_flatpage(self):
        "A flatpage can be served through a view, even when the middleware is in use"
        response = self.client.get('/flatpage_root/flatpage/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<p>Isn't it flat!</p>")

    def test_view_non_existent_flatpage(self):
        "A non-existent flatpage raises 404 when served through a view, even when the middleware is in use"
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
        "A flatpage can be served by the fallback middlware"
        response = self.client.get('/flatpage/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<p>Isn't it flat!</p>")

    def test_fallback_non_existent_flatpage(self):
        "A non-existent flatpage raises a 404 when served by the fallback middlware"
        response = self.client.get('/no_such_flatpage/')
        self.assertEqual(response.status_code, 404)

    def test_post_view_flatpage(self):
        "POSTing to a flatpage served through a view will raise a CSRF error if no token is provided (Refs #14156)"
        response = self.client.post('/flatpage_root/flatpage/')
        self.assertEqual(response.status_code, 403)

    def test_post_fallback_flatpage(self):
        "POSTing to a flatpage served by the middleware will raise a CSRF error if no token is provided (Refs #14156)"
        response = self.client.post('/flatpage/')
        self.assertEqual(response.status_code, 403)

    def test_post_unknown_page(self):
        "POSTing to an unknown page isn't caught as a 403 CSRF error"
        response = self.client.post('/no_such_page/')
        self.assertEqual(response.status_code, 404)
