import urllib
from django import db
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.contrib.contenttypes.views import shortcut
from django.http import HttpRequest, Http404
from django.test import TestCase
from django.db import models
from django.utils.encoding import smart_str


class FooWithoutUrl(models.Model):
    """
    Fake model not defining ``get_absolute_url`` for
    :meth:`ContentTypesTests.test_shortcut_view_without_get_absolute_url`"""
    name = models.CharField(max_length=30, unique=True)

    def __unicode__(self):
        return self.name


class FooWithUrl(FooWithoutUrl):
    """
    Fake model defining ``get_absolute_url`` for
    :meth:`ContentTypesTests.test_shortcut_view`
    """

    def get_absolute_url(self):
        return "/users/%s/" % urllib.quote(smart_str(self.name))


class ContentTypesTests(TestCase):

    def setUp(self):
        # First, let's make sure we're dealing with a blank slate (and that
        # DEBUG is on so that queries get logged)
        self.old_DEBUG = settings.DEBUG
        self.old_Site_meta_installed = Site._meta.installed
        settings.DEBUG = True
        ContentType.objects.clear_cache()
        db.reset_queries()

    def tearDown(self):
        settings.DEBUG = self.old_DEBUG
        Site._meta.installed = self.old_Site_meta_installed
        ContentType.objects.clear_cache()

    def test_lookup_cache(self):
        """
        Make sure that the content type cache (see ContentTypeManager)
        works correctly. Lookups for a particular content type -- by model or
        by ID -- should hit the database only on the first lookup.
        """

        # At this point, a lookup for a ContentType should hit the DB
        ContentType.objects.get_for_model(ContentType)
        self.assertEqual(1, len(db.connection.queries))

        # A second hit, though, won't hit the DB, nor will a lookup by ID
        ct = ContentType.objects.get_for_model(ContentType)
        self.assertEqual(1, len(db.connection.queries))
        ContentType.objects.get_for_id(ct.id)
        self.assertEqual(1, len(db.connection.queries))

        # Once we clear the cache, another lookup will again hit the DB
        ContentType.objects.clear_cache()
        ContentType.objects.get_for_model(ContentType)
        self.assertEqual(2, len(db.connection.queries))

    def test_shortcut_view(self):
        """
        Check that the shortcut view (used for the admin "view on site"
        functionality) returns a complete URL regardless of whether the sites
        framework is installed
        """

        request = HttpRequest()
        request.META = {
            "SERVER_NAME": "Example.com",
            "SERVER_PORT": "80",
        }
        user_ct = ContentType.objects.get_for_model(FooWithUrl)
        obj = FooWithUrl.objects.create(name="john")

        if Site._meta.installed:
            current_site = Site.objects.get_current()
            response = shortcut(request, user_ct.id, obj.id)
            self.assertEqual("http://%s/users/john/" % current_site.domain,
                             response._headers.get("location")[1])

        Site._meta.installed = False
        response = shortcut(request, user_ct.id, obj.id)
        self.assertEqual("http://Example.com/users/john/",
                         response._headers.get("location")[1])

    def test_shortcut_view_without_get_absolute_url(self):
        """
        Check that the shortcut view (used for the admin "view on site"
        functionality) returns 404 when get_absolute_url is not defined.
        """

        request = HttpRequest()
        request.META = {
            "SERVER_NAME": "Example.com",
            "SERVER_PORT": "80",
        }
        user_ct = ContentType.objects.get_for_model(FooWithoutUrl)
        obj = FooWithoutUrl.objects.create(name="john")

        self.assertRaises(Http404, shortcut, request, user_ct.id, obj.id)
