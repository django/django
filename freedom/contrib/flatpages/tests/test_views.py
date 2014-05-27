import os
from freedom.conf import settings
from freedom.contrib.auth.models import User
from freedom.contrib.auth.tests.utils import skipIfCustomUser
from freedom.contrib.flatpages.models import FlatPage
from freedom.test import TestCase, override_settings


@override_settings(
    LOGIN_URL='/accounts/login/',
    MIDDLEWARE_CLASSES=(
        'freedom.middleware.common.CommonMiddleware',
        'freedom.contrib.sessions.middleware.SessionMiddleware',
        'freedom.middleware.csrf.CsrfViewMiddleware',
        'freedom.contrib.auth.middleware.AuthenticationMiddleware',
        'freedom.contrib.messages.middleware.MessageMiddleware',
        # no 'freedom.contrib.flatpages.middleware.FlatpageFallbackMiddleware'
    ),
    ROOT_URLCONF='freedom.contrib.flatpages.tests.urls',
    TEMPLATE_DIRS=(
        os.path.join(os.path.dirname(__file__), 'templates'),
    ),
    SITE_ID=1,
)
class FlatpageViewTests(TestCase):
    fixtures = ['sample_flatpages', 'example_site']

    def test_view_flatpage(self):
        "A flatpage can be served through a view"
        response = self.client.get('/flatpage_root/flatpage/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<p>Isn't it flat!</p>")

    def test_view_non_existent_flatpage(self):
        "A non-existent flatpage raises 404 when served through a view"
        response = self.client.get('/flatpage_root/no_such_flatpage/')
        self.assertEqual(response.status_code, 404)

    @skipIfCustomUser
    def test_view_authenticated_flatpage(self):
        "A flatpage served through a view can require authentication"
        response = self.client.get('/flatpage_root/sekrit/')
        self.assertRedirects(response, '/accounts/login/?next=/flatpage_root/sekrit/')
        User.objects.create_user('testuser', 'test@example.com', 's3krit')
        self.client.login(username='testuser', password='s3krit')
        response = self.client.get('/flatpage_root/sekrit/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<p>Isn't it sekrit!</p>")

    def test_fallback_flatpage(self):
        "A fallback flatpage won't be served if the middleware is disabled"
        response = self.client.get('/flatpage/')
        self.assertEqual(response.status_code, 404)

    def test_fallback_non_existent_flatpage(self):
        "A non-existent flatpage won't be served if the fallback middleware is disabled"
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


@override_settings(
    APPEND_SLASH=True,
    LOGIN_URL='/accounts/login/',
    MIDDLEWARE_CLASSES=(
        'freedom.middleware.common.CommonMiddleware',
        'freedom.contrib.sessions.middleware.SessionMiddleware',
        'freedom.middleware.csrf.CsrfViewMiddleware',
        'freedom.contrib.auth.middleware.AuthenticationMiddleware',
        'freedom.contrib.messages.middleware.MessageMiddleware',
        # no 'freedom.contrib.flatpages.middleware.FlatpageFallbackMiddleware'
    ),
    ROOT_URLCONF='freedom.contrib.flatpages.tests.urls',
    TEMPLATE_DIRS=(
        os.path.join(os.path.dirname(__file__), 'templates'),
    ),
    SITE_ID=1,
)
class FlatpageViewAppendSlashTests(TestCase):
    fixtures = ['sample_flatpages', 'example_site']

    def test_redirect_view_flatpage(self):
        "A flatpage can be served through a view and should add a slash"
        response = self.client.get('/flatpage_root/flatpage')
        self.assertRedirects(response, '/flatpage_root/flatpage/', status_code=301)

    def test_redirect_view_non_existent_flatpage(self):
        "A non-existent flatpage raises 404 when served through a view and should not add a slash"
        response = self.client.get('/flatpage_root/no_such_flatpage')
        self.assertEqual(response.status_code, 404)

    def test_redirect_fallback_flatpage(self):
        "A fallback flatpage won't be served if the middleware is disabled and should not add a slash"
        response = self.client.get('/flatpage')
        self.assertEqual(response.status_code, 404)

    def test_redirect_fallback_non_existent_flatpage(self):
        "A non-existent flatpage won't be served if the fallback middleware is disabled and should not add a slash"
        response = self.client.get('/no_such_flatpage')
        self.assertEqual(response.status_code, 404)

    def test_redirect_view_flatpage_special_chars(self):
        "A flatpage with special chars in the URL can be served through a view and should add a slash"
        fp = FlatPage.objects.create(
            url="/some.very_special~chars-here/",
            title="A very special page",
            content="Isn't it special!",
            enable_comments=False,
            registration_required=False,
        )
        fp.sites.add(settings.SITE_ID)

        response = self.client.get('/flatpage_root/some.very_special~chars-here')
        self.assertRedirects(response, '/flatpage_root/some.very_special~chars-here/', status_code=301)
