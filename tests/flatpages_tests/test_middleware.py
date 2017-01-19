from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.test import TestCase, modify_settings, override_settings

from .settings import FLATPAGES_TEMPLATES


class TestDataMixin:

    @classmethod
    def setUpTestData(cls):
        # don't use the manager because we want to ensure the site exists
        # with pk=1, regardless of whether or not it already exists.
        cls.site1 = Site(pk=1, domain='example.com', name='example.com')
        cls.site1.save()
        cls.fp1 = FlatPage.objects.create(
            url='/flatpage/', title='A Flatpage', content="Isn't it flat!",
            enable_comments=False, template_name='', registration_required=False
        )
        cls.fp2 = FlatPage.objects.create(
            url='/location/flatpage/', title='A Nested Flatpage', content="Isn't it flat and deep!",
            enable_comments=False, template_name='', registration_required=False
        )
        cls.fp3 = FlatPage.objects.create(
            url='/sekrit/', title='Sekrit Flatpage', content="Isn't it sekrit!",
            enable_comments=False, template_name='', registration_required=True
        )
        cls.fp4 = FlatPage.objects.create(
            url='/location/sekrit/', title='Sekrit Nested Flatpage', content="Isn't it sekrit and deep!",
            enable_comments=False, template_name='', registration_required=True
        )
        cls.fp1.sites.add(cls.site1)
        cls.fp2.sites.add(cls.site1)
        cls.fp3.sites.add(cls.site1)
        cls.fp4.sites.add(cls.site1)


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.flatpages'})
@override_settings(
    LOGIN_URL='/accounts/login/',
    MIDDLEWARE=[
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    ],
    ROOT_URLCONF='flatpages_tests.urls',
    TEMPLATES=FLATPAGES_TEMPLATES,
    SITE_ID=1,
)
class FlatpageMiddlewareTests(TestDataMixin, TestCase):

    def test_view_flatpage(self):
        "A flatpage can be served through a view, even when the middleware is in use"
        response = self.client.get('/flatpage_root/flatpage/')
        self.assertContains(response, "<p>Isn't it flat!</p>")

    def test_view_non_existent_flatpage(self):
        "A non-existent flatpage raises 404 when served through a view, even when the middleware is in use"
        response = self.client.get('/flatpage_root/no_such_flatpage/')
        self.assertEqual(response.status_code, 404)

    def test_view_authenticated_flatpage(self):
        "A flatpage served through a view can require authentication"
        response = self.client.get('/flatpage_root/sekrit/')
        self.assertRedirects(response, '/accounts/login/?next=/flatpage_root/sekrit/')
        user = User.objects.create_user('testuser', 'test@example.com', 's3krit')
        self.client.force_login(user)
        response = self.client.get('/flatpage_root/sekrit/')
        self.assertContains(response, "<p>Isn't it sekrit!</p>")

    def test_fallback_flatpage(self):
        "A flatpage can be served by the fallback middleware"
        response = self.client.get('/flatpage/')
        self.assertContains(response, "<p>Isn't it flat!</p>")

    def test_fallback_non_existent_flatpage(self):
        "A non-existent flatpage raises a 404 when served by the fallback middleware"
        response = self.client.get('/no_such_flatpage/')
        self.assertEqual(response.status_code, 404)

    def test_fallback_authenticated_flatpage(self):
        "A flatpage served by the middleware can require authentication"
        response = self.client.get('/sekrit/')
        self.assertRedirects(response, '/accounts/login/?next=/sekrit/')
        user = User.objects.create_user('testuser', 'test@example.com', 's3krit')
        self.client.force_login(user)
        response = self.client.get('/sekrit/')
        self.assertContains(response, "<p>Isn't it sekrit!</p>")

    def test_fallback_flatpage_special_chars(self):
        "A flatpage with special chars in the URL can be served by the fallback middleware"
        fp = FlatPage.objects.create(
            url="/some.very_special~chars-here/",
            title="A very special page",
            content="Isn't it special!",
            enable_comments=False,
            registration_required=False,
        )
        fp.sites.add(settings.SITE_ID)

        response = self.client.get('/some.very_special~chars-here/')
        self.assertContains(response, "<p>Isn't it special!</p>")


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.flatpages'})
@override_settings(
    APPEND_SLASH=True,
    LOGIN_URL='/accounts/login/',
    MIDDLEWARE=[
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    ],
    ROOT_URLCONF='flatpages_tests.urls',
    TEMPLATES=FLATPAGES_TEMPLATES,
    SITE_ID=1,
)
class FlatpageMiddlewareAppendSlashTests(TestDataMixin, TestCase):

    def test_redirect_view_flatpage(self):
        "A flatpage can be served through a view and should add a slash"
        response = self.client.get('/flatpage_root/flatpage')
        self.assertRedirects(response, '/flatpage_root/flatpage/', status_code=301)

    def test_redirect_view_non_existent_flatpage(self):
        "A non-existent flatpage raises 404 when served through a view and should not add a slash"
        response = self.client.get('/flatpage_root/no_such_flatpage')
        self.assertEqual(response.status_code, 404)

    def test_redirect_fallback_flatpage(self):
        "A flatpage can be served by the fallback middleware and should add a slash"
        response = self.client.get('/flatpage')
        self.assertRedirects(response, '/flatpage/', status_code=301)

    def test_redirect_fallback_non_existent_flatpage(self):
        "A non-existent flatpage raises a 404 when served by the fallback middleware and should not add a slash"
        response = self.client.get('/no_such_flatpage')
        self.assertEqual(response.status_code, 404)

    def test_redirect_fallback_flatpage_special_chars(self):
        "A flatpage with special chars in the URL can be served by the fallback middleware and should add a slash"
        fp = FlatPage.objects.create(
            url="/some.very_special~chars-here/",
            title="A very special page",
            content="Isn't it special!",
            enable_comments=False,
            registration_required=False,
        )
        fp.sites.add(settings.SITE_ID)

        response = self.client.get('/some.very_special~chars-here')
        self.assertRedirects(response, '/some.very_special~chars-here/', status_code=301)

    def test_redirect_fallback_flatpage_root(self):
        "A flatpage at / should not cause a redirect loop when APPEND_SLASH is set"
        fp = FlatPage.objects.create(
            url="/",
            title="Root",
            content="Root",
            enable_comments=False,
            registration_required=False,
        )
        fp.sites.add(settings.SITE_ID)

        response = self.client.get('/')
        self.assertContains(response, "<p>Root</p>")
