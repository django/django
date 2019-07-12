import datetime

from django.contrib.sites.models import Site
from django.http import Http404
from django.template import TemplateDoesNotExist
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings
from django.views.defaults import (
    bad_request, page_not_found, permission_denied, server_error,
)

from ..models import Article, Author, UrlArticle


@override_settings(ROOT_URLCONF='view_tests.urls')
class DefaultsTests(TestCase):
    """Test django views in django/views/defaults.py"""
    nonexistent_urls = [
        '/nonexistent_url/',  # this is in urls.py
        '/other_nonexistent_url/',  # this NOT in urls.py
    ]
    request_factory = RequestFactory()

    @classmethod
    def setUpTestData(cls):
        Author.objects.create(name='Boris')
        Article.objects.create(
            title='Old Article', slug='old_article', author_id=1,
            date_created=datetime.datetime(2001, 1, 1, 21, 22, 23)
        )
        Article.objects.create(
            title='Current Article', slug='current_article', author_id=1,
            date_created=datetime.datetime(2007, 9, 17, 21, 22, 23)
        )
        Article.objects.create(
            title='Future Article', slug='future_article', author_id=1,
            date_created=datetime.datetime(3000, 1, 1, 21, 22, 23)
        )
        UrlArticle.objects.create(
            title='Old Article', slug='old_article', author_id=1,
            date_created=datetime.datetime(2001, 1, 1, 21, 22, 23)
        )
        Site(id=1, domain='testserver', name='testserver').save()

    def test_page_not_found(self):
        "A 404 status is returned by the page_not_found view"
        for url in self.nonexistent_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)
        self.assertIn(b'<h1>Not Found</h1>', response.content)
        self.assertIn(
            b'<p>The requested resource was not found on this server.</p>',
            response.content,
        )

    @override_settings(TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'loaders': [
                ('django.template.loaders.locmem.Loader', {
                    '404.html': '{{ csrf_token }}',
                }),
            ],
        },
    }])
    def test_csrf_token_in_404(self):
        """
        The 404 page should have the csrf_token available in the context
        """
        # See ticket #14565
        for url in self.nonexistent_urls:
            response = self.client.get(url)
            self.assertNotEqual(response.content, b'NOTPROVIDED')
            self.assertNotEqual(response.content, b'')

    def test_server_error(self):
        "The server_error view raises a 500 status"
        response = self.client.get('/server_error/')
        self.assertContains(response, b'<h1>Server Error (500)</h1>', status_code=500)

    def test_bad_request(self):
        request = self.request_factory.get('/')
        response = bad_request(request, Exception())
        self.assertContains(response, b'<h1>Bad Request (400)</h1>', status_code=400)

    @override_settings(TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'loaders': [
                ('django.template.loaders.locmem.Loader', {
                    '404.html': 'This is a test template for a 404 error '
                                '(path: {{ request_path }}, exception: {{ exception }}).',
                    '500.html': 'This is a test template for a 500 error.',
                }),
            ],
        },
    }])
    def test_custom_templates(self):
        """
        404.html and 500.html templates are picked by their respective handler.
        """
        response = self.client.get('/server_error/')
        self.assertContains(response, "test template for a 500 error", status_code=500)
        response = self.client.get('/no_such_url/')
        self.assertContains(response, 'path: /no_such_url/', status_code=404)
        self.assertContains(response, 'exception: Resolver404', status_code=404)
        response = self.client.get('/technical404/')
        self.assertContains(response, 'exception: Testing technical 404.', status_code=404)

    def test_get_absolute_url_attributes(self):
        "A model can set attributes on the get_absolute_url method"
        self.assertTrue(getattr(UrlArticle.get_absolute_url, 'purge', False),
                        'The attributes of the original get_absolute_url must be added.')
        article = UrlArticle.objects.get(pk=1)
        self.assertTrue(getattr(article.get_absolute_url, 'purge', False),
                        'The attributes of the original get_absolute_url must be added.')

    def test_custom_templates_wrong(self):
        """
        Default error views should raise TemplateDoesNotExist when passed a
        template that doesn't exist.
        """
        request = self.request_factory.get('/')

        with self.assertRaises(TemplateDoesNotExist):
            bad_request(request, Exception(), template_name='nonexistent')

        with self.assertRaises(TemplateDoesNotExist):
            permission_denied(request, Exception(), template_name='nonexistent')

        with self.assertRaises(TemplateDoesNotExist):
            page_not_found(request, Http404(), template_name='nonexistent')

        with self.assertRaises(TemplateDoesNotExist):
            server_error(request, template_name='nonexistent')

    def test_error_pages(self):
        request = self.request_factory.get('/')
        for response, title in (
            (bad_request(request, Exception()), b'Bad Request (400)'),
            (permission_denied(request, Exception()), b'403 Forbidden'),
            (page_not_found(request, Http404()), b'Not Found'),
            (server_error(request), b'Server Error (500)'),
        ):
            with self.subTest(title=title):
                self.assertIn(b'<!doctype html>', response.content)
                self.assertIn(b'<html lang="en">', response.content)
                self.assertIn(b'<head>', response.content)
                self.assertIn(b'<title>%s</title>' % title, response.content)
                self.assertIn(b'<body>', response.content)
