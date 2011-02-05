from django import db
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.contrib.contenttypes.views import shortcut
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest
from django.test import TestCase


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
        len(db.connection.queries)
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
        from django.contrib.auth.models import User
        user_ct = ContentType.objects.get_for_model(User)
        obj = User.objects.create(username="john")

        if Site._meta.installed:
            response = shortcut(request, user_ct.id, obj.id)
            self.assertEqual("http://example.com/users/john/", response._headers.get("location")[1])

        Site._meta.installed = False
        response = shortcut(request, user_ct.id, obj.id)
        self.assertEqual("http://Example.com/users/john/", response._headers.get("location")[1])
