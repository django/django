from django.contrib.contenttypes.models import ContentType, ContentTypeManager
from django.contrib.contenttypes.views import shortcut
from django.contrib.sites.shortcuts import get_current_site
from django.db import connections
from django.http import Http404, HttpRequest
from django.test import TestCase, override_settings

from .models import (
    Author, ConcreteModel, FooWithBrokenAbsoluteUrl, FooWithoutUrl, FooWithUrl,
    ProxyModel,
)


class ContentTypesTests(TestCase):

    def setUp(self):
        ContentType.objects.clear_cache()

    def tearDown(self):
        ContentType.objects.clear_cache()

    def test_lookup_cache(self):
        """
        The content type cache (see ContentTypeManager) works correctly.
        Lookups for a particular content type -- by model, ID, or natural key
        -- should hit the database only on the first lookup.
        """
        # At this point, a lookup for a ContentType should hit the DB
        with self.assertNumQueries(1):
            ContentType.objects.get_for_model(ContentType)

        # A second hit, though, won't hit the DB, nor will a lookup by ID
        # or natural key
        with self.assertNumQueries(0):
            ct = ContentType.objects.get_for_model(ContentType)
        with self.assertNumQueries(0):
            ContentType.objects.get_for_id(ct.id)
        with self.assertNumQueries(0):
            ContentType.objects.get_by_natural_key('contenttypes', 'contenttype')

        # Once we clear the cache, another lookup will again hit the DB
        ContentType.objects.clear_cache()
        with self.assertNumQueries(1):
            ContentType.objects.get_for_model(ContentType)

        # The same should happen with a lookup by natural key
        ContentType.objects.clear_cache()
        with self.assertNumQueries(1):
            ContentType.objects.get_by_natural_key('contenttypes', 'contenttype')
        # And a second hit shouldn't hit the DB
        with self.assertNumQueries(0):
            ContentType.objects.get_by_natural_key('contenttypes', 'contenttype')

    def test_get_for_models_creation(self):
        ContentType.objects.all().delete()
        with self.assertNumQueries(4):
            cts = ContentType.objects.get_for_models(ContentType, FooWithUrl, ProxyModel, ConcreteModel)
        self.assertEqual(cts, {
            ContentType: ContentType.objects.get_for_model(ContentType),
            FooWithUrl: ContentType.objects.get_for_model(FooWithUrl),
            ProxyModel: ContentType.objects.get_for_model(ProxyModel),
            ConcreteModel: ContentType.objects.get_for_model(ConcreteModel),
        })

    def test_get_for_models_empty_cache(self):
        # Empty cache.
        with self.assertNumQueries(1):
            cts = ContentType.objects.get_for_models(ContentType, FooWithUrl, ProxyModel, ConcreteModel)
        self.assertEqual(cts, {
            ContentType: ContentType.objects.get_for_model(ContentType),
            FooWithUrl: ContentType.objects.get_for_model(FooWithUrl),
            ProxyModel: ContentType.objects.get_for_model(ProxyModel),
            ConcreteModel: ContentType.objects.get_for_model(ConcreteModel),
        })

    def test_get_for_models_partial_cache(self):
        # Partial cache
        ContentType.objects.get_for_model(ContentType)
        with self.assertNumQueries(1):
            cts = ContentType.objects.get_for_models(ContentType, FooWithUrl)
        self.assertEqual(cts, {
            ContentType: ContentType.objects.get_for_model(ContentType),
            FooWithUrl: ContentType.objects.get_for_model(FooWithUrl),
        })

    def test_get_for_models_full_cache(self):
        # Full cache
        ContentType.objects.get_for_model(ContentType)
        ContentType.objects.get_for_model(FooWithUrl)
        with self.assertNumQueries(0):
            cts = ContentType.objects.get_for_models(ContentType, FooWithUrl)
        self.assertEqual(cts, {
            ContentType: ContentType.objects.get_for_model(ContentType),
            FooWithUrl: ContentType.objects.get_for_model(FooWithUrl),
        })

    def test_get_for_concrete_model(self):
        """
        Make sure the `for_concrete_model` kwarg correctly works
        with concrete, proxy and deferred models
        """
        concrete_model_ct = ContentType.objects.get_for_model(ConcreteModel)
        self.assertEqual(concrete_model_ct, ContentType.objects.get_for_model(ProxyModel))
        self.assertEqual(concrete_model_ct, ContentType.objects.get_for_model(ConcreteModel, for_concrete_model=False))

        proxy_model_ct = ContentType.objects.get_for_model(ProxyModel, for_concrete_model=False)
        self.assertNotEqual(concrete_model_ct, proxy_model_ct)

        # Make sure deferred model are correctly handled
        ConcreteModel.objects.create(name="Concrete")
        DeferredConcreteModel = ConcreteModel.objects.only('pk').get().__class__
        DeferredProxyModel = ProxyModel.objects.only('pk').get().__class__

        self.assertEqual(concrete_model_ct, ContentType.objects.get_for_model(DeferredConcreteModel))
        self.assertEqual(
            concrete_model_ct,
            ContentType.objects.get_for_model(DeferredConcreteModel, for_concrete_model=False)
        )
        self.assertEqual(concrete_model_ct, ContentType.objects.get_for_model(DeferredProxyModel))
        self.assertEqual(
            proxy_model_ct,
            ContentType.objects.get_for_model(DeferredProxyModel, for_concrete_model=False)
        )

    def test_get_for_concrete_models(self):
        """
        Make sure the `for_concrete_models` kwarg correctly works
        with concrete, proxy and deferred models.
        """
        concrete_model_ct = ContentType.objects.get_for_model(ConcreteModel)

        cts = ContentType.objects.get_for_models(ConcreteModel, ProxyModel)
        self.assertEqual(cts, {
            ConcreteModel: concrete_model_ct,
            ProxyModel: concrete_model_ct,
        })

        proxy_model_ct = ContentType.objects.get_for_model(ProxyModel, for_concrete_model=False)
        cts = ContentType.objects.get_for_models(ConcreteModel, ProxyModel, for_concrete_models=False)
        self.assertEqual(cts, {
            ConcreteModel: concrete_model_ct,
            ProxyModel: proxy_model_ct,
        })

        # Make sure deferred model are correctly handled
        ConcreteModel.objects.create(name="Concrete")
        DeferredConcreteModel = ConcreteModel.objects.only('pk').get().__class__
        DeferredProxyModel = ProxyModel.objects.only('pk').get().__class__

        cts = ContentType.objects.get_for_models(DeferredConcreteModel, DeferredProxyModel)
        self.assertEqual(cts, {
            DeferredConcreteModel: concrete_model_ct,
            DeferredProxyModel: concrete_model_ct,
        })

        cts = ContentType.objects.get_for_models(
            DeferredConcreteModel, DeferredProxyModel, for_concrete_models=False
        )
        self.assertEqual(cts, {
            DeferredConcreteModel: concrete_model_ct,
            DeferredProxyModel: proxy_model_ct,
        })

    def test_cache_not_shared_between_managers(self):
        with self.assertNumQueries(1):
            ContentType.objects.get_for_model(ContentType)
        with self.assertNumQueries(0):
            ContentType.objects.get_for_model(ContentType)
        other_manager = ContentTypeManager()
        other_manager.model = ContentType
        with self.assertNumQueries(1):
            other_manager.get_for_model(ContentType)
        with self.assertNumQueries(0):
            other_manager.get_for_model(ContentType)

    @override_settings(ALLOWED_HOSTS=['example.com'])
    def test_shortcut_view(self):
        """
        The shortcut view (used for the admin "view on site" functionality)
        returns a complete URL regardless of whether the sites framework is
        installed.
        """
        request = HttpRequest()
        request.META = {
            "SERVER_NAME": "Example.com",
            "SERVER_PORT": "80",
        }
        user_ct = ContentType.objects.get_for_model(FooWithUrl)
        obj = FooWithUrl.objects.create(name="john")

        with self.modify_settings(INSTALLED_APPS={'append': 'django.contrib.sites'}):
            response = shortcut(request, user_ct.id, obj.id)
            self.assertEqual(
                "http://%s/users/john/" % get_current_site(request).domain,
                response._headers.get("location")[1]
            )

        with self.modify_settings(INSTALLED_APPS={'remove': 'django.contrib.sites'}):
            response = shortcut(request, user_ct.id, obj.id)
            self.assertEqual("http://Example.com/users/john/", response._headers.get("location")[1])

    def test_shortcut_view_without_get_absolute_url(self):
        """
        The shortcut view (used for the admin "view on site" functionality)
        returns 404 when get_absolute_url is not defined.
        """
        request = HttpRequest()
        request.META = {
            "SERVER_NAME": "Example.com",
            "SERVER_PORT": "80",
        }
        user_ct = ContentType.objects.get_for_model(FooWithoutUrl)
        obj = FooWithoutUrl.objects.create(name="john")

        with self.assertRaises(Http404):
            shortcut(request, user_ct.id, obj.id)

    def test_shortcut_view_with_broken_get_absolute_url(self):
        """
        The shortcut view does not catch an AttributeError raised by
        the model's get_absolute_url() method (#8997).
        """
        request = HttpRequest()
        request.META = {
            "SERVER_NAME": "Example.com",
            "SERVER_PORT": "80",
        }
        user_ct = ContentType.objects.get_for_model(FooWithBrokenAbsoluteUrl)
        obj = FooWithBrokenAbsoluteUrl.objects.create(name="john")

        with self.assertRaises(AttributeError):
            shortcut(request, user_ct.id, obj.id)

    def test_missing_model(self):
        """
        Displaying content types in admin (or anywhere) doesn't break on
        leftover content type records in the DB for which no model is defined
        anymore.
        """
        ct = ContentType.objects.create(
            app_label='contenttypes',
            model='OldModel',
        )
        self.assertEqual(str(ct), 'OldModel')
        self.assertIsNone(ct.model_class())

        # Stale ContentTypes can be fetched like any other object.
        ct_fetched = ContentType.objects.get_for_id(ct.pk)
        self.assertIsNone(ct_fetched.model_class())


class TestRouter:
    def db_for_read(self, model, **hints):
        return 'other'

    def db_for_write(self, model, **hints):
        return 'default'


@override_settings(DATABASE_ROUTERS=[TestRouter()])
class ContentTypesMultidbTests(TestCase):

    def setUp(self):
        # When a test starts executing, only the "default" database is
        # connected. Connect to the "other" database here because otherwise it
        # will be connected later when it's queried. Some database backends
        # perform extra queries upon connecting (MySQL executes
        # "SET SQL_AUTO_IS_NULL = 0"), which will affect assertNumQueries().
        connections['other'].ensure_connection()

    def test_multidb(self):
        """
        When using multiple databases, ContentType.objects.get_for_model() uses
        db_for_read().
        """
        ContentType.objects.clear_cache()
        with self.assertNumQueries(0, using='default'), self.assertNumQueries(1, using='other'):
            ContentType.objects.get_for_model(Author)
