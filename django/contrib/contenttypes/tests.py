from __future__ import unicode_literals

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.views import shortcut
from django.contrib.sites.models import Site, get_current_site
from django.http import HttpRequest, Http404
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.http import urlquote
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible


class ConcreteModel(models.Model):
    name = models.CharField(max_length=10)

class ProxyModel(ConcreteModel):
    class Meta:
        proxy = True

@python_2_unicode_compatible
class FooWithoutUrl(models.Model):
    """
    Fake model not defining ``get_absolute_url`` for
    :meth:`ContentTypesTests.test_shortcut_view_without_get_absolute_url`"""
    name = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name


class FooWithUrl(FooWithoutUrl):
    """
    Fake model defining ``get_absolute_url`` for
    :meth:`ContentTypesTests.test_shortcut_view`
    """

    def get_absolute_url(self):
        return "/users/%s/" % urlquote(self.name)

class FooWithBrokenAbsoluteUrl(FooWithoutUrl):
    """
    Fake model defining a ``get_absolute_url`` method containing an error
    """

    def get_absolute_url(self):
        return "/users/%s/" % self.unknown_field

class ContentTypesTests(TestCase):

    def setUp(self):
        self.old_Site_meta_installed = Site._meta.installed
        ContentType.objects.clear_cache()

    def tearDown(self):
        Site._meta.installed = self.old_Site_meta_installed
        ContentType.objects.clear_cache()

    def test_lookup_cache(self):
        """
        Make sure that the content type cache (see ContentTypeManager)
        works correctly. Lookups for a particular content type -- by model, ID
        or natural key -- should hit the database only on the first lookup.
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
            ContentType.objects.get_by_natural_key('contenttypes',
                                                   'contenttype')

        # Once we clear the cache, another lookup will again hit the DB
        ContentType.objects.clear_cache()
        with self.assertNumQueries(1):
            ContentType.objects.get_for_model(ContentType)

        # The same should happen with a lookup by natural key
        ContentType.objects.clear_cache()
        with self.assertNumQueries(1):
            ContentType.objects.get_by_natural_key('contenttypes',
                                                   'contenttype')
        # And a second hit shouldn't hit the DB
        with self.assertNumQueries(0):
            ContentType.objects.get_by_natural_key('contenttypes',
                                                   'contenttype')

    def test_get_for_models_empty_cache(self):
        # Empty cache.
        with self.assertNumQueries(1):
            cts = ContentType.objects.get_for_models(ContentType, FooWithUrl)
        self.assertEqual(cts, {
            ContentType: ContentType.objects.get_for_model(ContentType),
            FooWithUrl: ContentType.objects.get_for_model(FooWithUrl),
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

        self.assertEqual(concrete_model_ct,
            ContentType.objects.get_for_model(ProxyModel))

        self.assertEqual(concrete_model_ct,
            ContentType.objects.get_for_model(ConcreteModel,
                                              for_concrete_model=False))

        proxy_model_ct = ContentType.objects.get_for_model(ProxyModel,
                                                           for_concrete_model=False)

        self.assertNotEqual(concrete_model_ct, proxy_model_ct)

        # Make sure deferred model are correctly handled
        ConcreteModel.objects.create(name="Concrete")
        DeferredConcreteModel = ConcreteModel.objects.only('pk').get().__class__
        DeferredProxyModel = ProxyModel.objects.only('pk').get().__class__

        self.assertEqual(concrete_model_ct,
            ContentType.objects.get_for_model(DeferredConcreteModel))

        self.assertEqual(concrete_model_ct,
            ContentType.objects.get_for_model(DeferredConcreteModel,
                                              for_concrete_model=False))

        self.assertEqual(concrete_model_ct,
            ContentType.objects.get_for_model(DeferredProxyModel))

        self.assertEqual(proxy_model_ct,
            ContentType.objects.get_for_model(DeferredProxyModel,
                                              for_concrete_model=False))

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

        proxy_model_ct = ContentType.objects.get_for_model(ProxyModel,
                                                           for_concrete_model=False)
        cts = ContentType.objects.get_for_models(ConcreteModel, ProxyModel,
                                                 for_concrete_models=False)
        self.assertEqual(cts, {
            ConcreteModel: concrete_model_ct,
            ProxyModel: proxy_model_ct,
        })

        # Make sure deferred model are correctly handled
        ConcreteModel.objects.create(name="Concrete")
        DeferredConcreteModel = ConcreteModel.objects.only('pk').get().__class__
        DeferredProxyModel = ProxyModel.objects.only('pk').get().__class__

        cts = ContentType.objects.get_for_models(DeferredConcreteModel,
                                                 DeferredProxyModel)
        self.assertEqual(cts, {
            DeferredConcreteModel: concrete_model_ct,
            DeferredProxyModel: concrete_model_ct,
        })

        cts = ContentType.objects.get_for_models(DeferredConcreteModel,
                                                 DeferredProxyModel,
                                                 for_concrete_models=False)
        self.assertEqual(cts, {
            DeferredConcreteModel: concrete_model_ct,
            DeferredProxyModel: proxy_model_ct,
        })


    @override_settings(ALLOWED_HOSTS=['example.com'])
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
            response = shortcut(request, user_ct.id, obj.id)
            self.assertEqual("http://%s/users/john/" % get_current_site(request).domain,
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

    def test_shortcut_view_with_broken_get_absolute_url(self):
        """
        Check that the shortcut view does not catch an AttributeError raised
        by the model's get_absolute_url method.
        Refs #8997.
        """
        request = HttpRequest()
        request.META = {
            "SERVER_NAME": "Example.com",
            "SERVER_PORT": "80",
        }
        user_ct = ContentType.objects.get_for_model(FooWithBrokenAbsoluteUrl)
        obj = FooWithBrokenAbsoluteUrl.objects.create(name="john")

        self.assertRaises(AttributeError, shortcut, request, user_ct.id, obj.id)

    def test_missing_model(self):
        """
        Ensures that displaying content types in admin (or anywhere) doesn't
        break on leftover content type records in the DB for which no model
        is defined anymore.
        """
        ct = ContentType.objects.create(
            name = 'Old model',
            app_label = 'contenttypes',
            model = 'OldModel',
        )
        self.assertEqual(six.text_type(ct), 'Old model')
