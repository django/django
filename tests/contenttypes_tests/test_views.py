import datetime
from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.views import shortcut
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from django.http import Http404, HttpRequest
from django.test import TestCase, override_settings

from .models import (
    Article,
    Author,
    FooWithBrokenAbsoluteUrl,
    FooWithoutUrl,
    FooWithUrl,
    ModelWithM2MToSite,
    ModelWithNullFKToSite,
    SchemeIncludedURL,
)
from .models import Site as MockSite


@override_settings(ROOT_URLCONF="contenttypes_tests.urls")
class ContentTypesViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Don't use the manager to ensure the site exists with pk=1, regardless
        # of whether or not it already exists.
        cls.site1 = Site(pk=1, domain="testserver", name="testserver")
        cls.site1.save()
        cls.author1 = Author.objects.create(name="Boris")
        cls.article1 = Article.objects.create(
            title="Old Article",
            slug="old_article",
            author=cls.author1,
            date_created=datetime.datetime(2001, 1, 1, 21, 22, 23),
        )
        cls.article2 = Article.objects.create(
            title="Current Article",
            slug="current_article",
            author=cls.author1,
            date_created=datetime.datetime(2007, 9, 17, 21, 22, 23),
        )
        cls.article3 = Article.objects.create(
            title="Future Article",
            slug="future_article",
            author=cls.author1,
            date_created=datetime.datetime(3000, 1, 1, 21, 22, 23),
        )
        cls.scheme1 = SchemeIncludedURL.objects.create(
            url="http://test_scheme_included_http/"
        )
        cls.scheme2 = SchemeIncludedURL.objects.create(
            url="https://test_scheme_included_https/"
        )
        cls.scheme3 = SchemeIncludedURL.objects.create(
            url="//test_default_scheme_kept/"
        )

    def setUp(self):
        Site.objects.clear_cache()

    def test_shortcut_with_absolute_url(self):
        "Can view a shortcut for an Author object that has a get_absolute_url method"
        for obj in Author.objects.all():
            with self.subTest(obj=obj):
                short_url = "/shortcut/%s/%s/" % (
                    ContentType.objects.get_for_model(Author).id,
                    obj.pk,
                )
                response = self.client.get(short_url)
                self.assertRedirects(
                    response,
                    "http://testserver%s" % obj.get_absolute_url(),
                    target_status_code=404,
                )

    def test_shortcut_with_absolute_url_including_scheme(self):
        """
        Can view a shortcut when object's get_absolute_url returns a full URL
        the tested URLs are: "http://...", "https://..." and "//..."
        """
        for obj in SchemeIncludedURL.objects.all():
            with self.subTest(obj=obj):
                short_url = "/shortcut/%s/%s/" % (
                    ContentType.objects.get_for_model(SchemeIncludedURL).id,
                    obj.pk,
                )
                response = self.client.get(short_url)
                self.assertRedirects(
                    response, obj.get_absolute_url(), fetch_redirect_response=False
                )

    def test_shortcut_no_absolute_url(self):
        """
        Shortcuts for an object that has no get_absolute_url() method raise
        404.
        """
        for obj in Article.objects.all():
            with self.subTest(obj=obj):
                short_url = "/shortcut/%s/%s/" % (
                    ContentType.objects.get_for_model(Article).id,
                    obj.pk,
                )
                response = self.client.get(short_url)
                self.assertEqual(response.status_code, 404)

    def test_wrong_type_pk(self):
        short_url = "/shortcut/%s/%s/" % (
            ContentType.objects.get_for_model(Author).id,
            "nobody/expects",
        )
        response = self.client.get(short_url)
        self.assertEqual(response.status_code, 404)

    def test_shortcut_bad_pk(self):
        short_url = "/shortcut/%s/%s/" % (
            ContentType.objects.get_for_model(Author).id,
            "42424242",
        )
        response = self.client.get(short_url)
        self.assertEqual(response.status_code, 404)

    def test_nonint_content_type(self):
        an_author = Author.objects.all()[0]
        short_url = "/shortcut/%s/%s/" % ("spam", an_author.pk)
        response = self.client.get(short_url)
        self.assertEqual(response.status_code, 404)

    def test_bad_content_type(self):
        an_author = Author.objects.all()[0]
        short_url = "/shortcut/%s/%s/" % (42424242, an_author.pk)
        response = self.client.get(short_url)
        self.assertEqual(response.status_code, 404)


@override_settings(ROOT_URLCONF="contenttypes_tests.urls")
class ContentTypesViewsSiteRelTests(TestCase):
    def setUp(self):
        Site.objects.clear_cache()

    @classmethod
    def setUpTestData(cls):
        cls.site_2 = Site.objects.create(domain="example2.com", name="example2.com")
        cls.site_3 = Site.objects.create(domain="example3.com", name="example3.com")

    @mock.patch("django.apps.apps.get_model")
    def test_shortcut_view_with_null_site_fk(self, get_model):
        """
        The shortcut view works if a model's ForeignKey to site is None.
        """
        get_model.side_effect = lambda *args, **kwargs: (
            MockSite if args[0] == "sites.Site" else ModelWithNullFKToSite
        )

        obj = ModelWithNullFKToSite.objects.create(title="title")
        url = "/shortcut/%s/%s/" % (
            ContentType.objects.get_for_model(ModelWithNullFKToSite).id,
            obj.pk,
        )
        response = self.client.get(url)
        expected_url = "http://example.com%s" % obj.get_absolute_url()
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)

    @mock.patch("django.apps.apps.get_model")
    def test_shortcut_view_with_site_m2m(self, get_model):
        """
        When the object has a ManyToManyField to Site, redirect to the current
        site if it's attached to the object or to the domain of the first site
        found in the m2m relationship.
        """
        get_model.side_effect = lambda *args, **kwargs: (
            MockSite if args[0] == "sites.Site" else ModelWithM2MToSite
        )

        # get_current_site() will lookup a Site object, so these must match the
        # domains in the MockSite model.
        MockSite.objects.bulk_create(
            [
                MockSite(pk=1, domain="example.com"),
                MockSite(pk=self.site_2.pk, domain=self.site_2.domain),
                MockSite(pk=self.site_3.pk, domain=self.site_3.domain),
            ]
        )
        ct = ContentType.objects.get_for_model(ModelWithM2MToSite)
        site_3_obj = ModelWithM2MToSite.objects.create(
            title="Not Linked to Current Site"
        )
        site_3_obj.sites.add(MockSite.objects.get(pk=self.site_3.pk))
        expected_url = "http://%s%s" % (
            self.site_3.domain,
            site_3_obj.get_absolute_url(),
        )

        with self.settings(SITE_ID=self.site_2.pk):
            # Redirects to the domain of the first Site found in the m2m
            # relationship (ordering is arbitrary).
            response = self.client.get("/shortcut/%s/%s/" % (ct.pk, site_3_obj.pk))
            self.assertRedirects(response, expected_url, fetch_redirect_response=False)

        obj_with_sites = ModelWithM2MToSite.objects.create(
            title="Linked to Current Site"
        )
        obj_with_sites.sites.set(MockSite.objects.all())
        shortcut_url = "/shortcut/%s/%s/" % (ct.pk, obj_with_sites.pk)
        expected_url = "http://%s%s" % (
            self.site_2.domain,
            obj_with_sites.get_absolute_url(),
        )

        with self.settings(SITE_ID=self.site_2.pk):
            # Redirects to the domain of the Site matching the current site's
            # domain.
            response = self.client.get(shortcut_url)
            self.assertRedirects(response, expected_url, fetch_redirect_response=False)

        with self.settings(SITE_ID=None, ALLOWED_HOSTS=[self.site_2.domain]):
            # Redirects to the domain of the Site matching the request's host
            # header.
            response = self.client.get(shortcut_url, SERVER_NAME=self.site_2.domain)
            self.assertRedirects(response, expected_url, fetch_redirect_response=False)


class ShortcutViewTests(TestCase):
    def setUp(self):
        self.request = HttpRequest()
        self.request.META = {"SERVER_NAME": "Example.com", "SERVER_PORT": "80"}

    @override_settings(ALLOWED_HOSTS=["example.com"])
    def test_not_dependent_on_sites_app(self):
        """
        The view returns a complete URL regardless of whether the sites
        framework is installed.
        """
        user_ct = ContentType.objects.get_for_model(FooWithUrl)
        obj = FooWithUrl.objects.create(name="john")
        with self.modify_settings(INSTALLED_APPS={"append": "django.contrib.sites"}):
            response = shortcut(self.request, user_ct.id, obj.id)
            self.assertEqual(
                "http://%s/users/john/" % get_current_site(self.request).domain,
                response.headers.get("location"),
            )
        with self.modify_settings(INSTALLED_APPS={"remove": "django.contrib.sites"}):
            response = shortcut(self.request, user_ct.id, obj.id)
            self.assertEqual(
                "http://Example.com/users/john/", response.headers.get("location")
            )

    def test_model_without_get_absolute_url(self):
        """The view returns 404 when Model.get_absolute_url() isn't defined."""
        user_ct = ContentType.objects.get_for_model(FooWithoutUrl)
        obj = FooWithoutUrl.objects.create(name="john")
        with self.assertRaises(Http404):
            shortcut(self.request, user_ct.id, obj.id)

    def test_model_with_broken_get_absolute_url(self):
        """
        The view doesn't catch an AttributeError raised by
        Model.get_absolute_url() (#8997).
        """
        user_ct = ContentType.objects.get_for_model(FooWithBrokenAbsoluteUrl)
        obj = FooWithBrokenAbsoluteUrl.objects.create(name="john")
        with self.assertRaises(AttributeError):
            shortcut(self.request, user_ct.id, obj.id)
