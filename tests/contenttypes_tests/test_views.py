import datetime
from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db import models
from django.test import TestCase, override_settings
from django.test.utils import isolate_apps

from .models import (
    Article, Author, ModelWithNullFKToSite, SchemeIncludedURL,
    Site as MockSite,
)


@override_settings(ROOT_URLCONF='contenttypes_tests.urls')
class ContentTypesViewsTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Don't use the manager to ensure the site exists with pk=1, regardless
        # of whether or not it already exists.
        cls.site1 = Site(pk=1, domain='testserver', name='testserver')
        cls.site1.save()
        cls.author1 = Author.objects.create(name='Boris')
        cls.article1 = Article.objects.create(
            title='Old Article', slug='old_article', author=cls.author1,
            date_created=datetime.datetime(2001, 1, 1, 21, 22, 23),
        )
        cls.article2 = Article.objects.create(
            title='Current Article', slug='current_article', author=cls.author1,
            date_created=datetime.datetime(2007, 9, 17, 21, 22, 23),
        )
        cls.article3 = Article.objects.create(
            title='Future Article', slug='future_article', author=cls.author1,
            date_created=datetime.datetime(3000, 1, 1, 21, 22, 23),
        )
        cls.scheme1 = SchemeIncludedURL.objects.create(url='http://test_scheme_included_http/')
        cls.scheme2 = SchemeIncludedURL.objects.create(url='https://test_scheme_included_https/')
        cls.scheme3 = SchemeIncludedURL.objects.create(url='//test_default_scheme_kept/')

    def setUp(self):
        Site.objects.clear_cache()

    def test_shortcut_with_absolute_url(self):
        "Can view a shortcut for an Author object that has a get_absolute_url method"
        for obj in Author.objects.all():
            with self.subTest(obj=obj):
                short_url = '/shortcut/%s/%s/' % (ContentType.objects.get_for_model(Author).id, obj.pk)
                response = self.client.get(short_url)
                self.assertRedirects(response, 'http://testserver%s' % obj.get_absolute_url(), target_status_code=404)

    def test_shortcut_with_absolute_url_including_scheme(self):
        """
        Can view a shortcut when object's get_absolute_url returns a full URL
        the tested URLs are: "http://...", "https://..." and "//..."
        """
        for obj in SchemeIncludedURL.objects.all():
            with self.subTest(obj=obj):
                short_url = '/shortcut/%s/%s/' % (ContentType.objects.get_for_model(SchemeIncludedURL).id, obj.pk)
                response = self.client.get(short_url)
                self.assertRedirects(response, obj.get_absolute_url(), fetch_redirect_response=False)

    def test_shortcut_no_absolute_url(self):
        """
        Shortcuts for an object that has no get_absolute_url() method raise
        404.
        """
        for obj in Article.objects.all():
            with self.subTest(obj=obj):
                short_url = '/shortcut/%s/%s/' % (ContentType.objects.get_for_model(Article).id, obj.pk)
                response = self.client.get(short_url)
                self.assertEqual(response.status_code, 404)

    def test_wrong_type_pk(self):
        short_url = '/shortcut/%s/%s/' % (ContentType.objects.get_for_model(Author).id, 'nobody/expects')
        response = self.client.get(short_url)
        self.assertEqual(response.status_code, 404)

    def test_shortcut_bad_pk(self):
        short_url = '/shortcut/%s/%s/' % (ContentType.objects.get_for_model(Author).id, '42424242')
        response = self.client.get(short_url)
        self.assertEqual(response.status_code, 404)

    def test_nonint_content_type(self):
        an_author = Author.objects.all()[0]
        short_url = '/shortcut/%s/%s/' % ('spam', an_author.pk)
        response = self.client.get(short_url)
        self.assertEqual(response.status_code, 404)

    def test_bad_content_type(self):
        an_author = Author.objects.all()[0]
        short_url = '/shortcut/%s/%s/' % (42424242, an_author.pk)
        response = self.client.get(short_url)
        self.assertEqual(response.status_code, 404)

    @mock.patch('django.apps.apps.get_model')
    def test_shortcut_view_with_null_site_fk(self, get_model):
        """
        The shortcut view works if a model's ForeignKey to site is None.
        """
        get_model.side_effect = lambda *args, **kwargs: MockSite if args[0] == 'sites.Site' else ModelWithNullFKToSite

        obj = ModelWithNullFKToSite.objects.create(title='title')
        url = '/shortcut/%s/%s/' % (ContentType.objects.get_for_model(ModelWithNullFKToSite).id, obj.pk)
        response = self.client.get(url)
        self.assertRedirects(response, '%s' % obj.get_absolute_url(), fetch_redirect_response=False)

    @isolate_apps('contenttypes_tests')
    def test_create_contenttype_on_the_spot(self):
        """
        ContentTypeManager.get_for_model() creates the corresponding content
        type if it doesn't exist in the database.
        """
        class ModelCreatedOnTheFly(models.Model):
            name = models.CharField()

            class Meta:
                verbose_name = 'a model created on the fly'

        ct = ContentType.objects.get_for_model(ModelCreatedOnTheFly)
        self.assertEqual(ct.app_label, 'contenttypes_tests')
        self.assertEqual(ct.model, 'modelcreatedonthefly')
        self.assertEqual(str(ct), 'modelcreatedonthefly')
