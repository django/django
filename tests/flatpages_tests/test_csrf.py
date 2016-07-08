from django.contrib.auth.models import User
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.test import Client, TestCase, modify_settings, override_settings
from django.test.utils import ignore_warnings
from django.utils.deprecation import RemovedInDjango20Warning

from .settings import FLATPAGES_TEMPLATES


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
    CSRF_FAILURE_VIEW='django.views.csrf.csrf_failure',
    TEMPLATES=FLATPAGES_TEMPLATES,
    SITE_ID=1,
)
class FlatpageCSRFTests(TestCase):

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

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

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


@ignore_warnings(category=RemovedInDjango20Warning)
@override_settings(
    MIDDLEWARE=None,
    MIDDLEWARE_CLASSES=[
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    ],
)
class FlatpageCSRFMiddlewareClassesTests(FlatpageCSRFTests):
    pass
