from __future__ import unicode_literals

import datetime

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase
from django.test.utils import override_settings

from ..models import Article, Author, UrlArticle


@override_settings(ROOT_URLCONF='view_tests.urls')
class DefaultsTests(TestCase):
    """Test django views in django/views/defaults.py"""
    non_existing_urls = ['/non_existing_url/',  # this is in urls.py
                         '/other_non_existing_url/']  # this NOT in urls.py

    @classmethod
    def setUpTestData(cls):
        User.objects.create(
            password='sha1$6efc0$f93efe9fd7542f25a7be94871ea45aa95de57161',
            last_login=datetime.datetime(2006, 12, 17, 7, 3, 31), is_superuser=False, username='testclient',
            first_name='Test', last_name='Client', email='testclient@example.com', is_staff=False, is_active=True,
            date_joined=datetime.datetime(2006, 12, 17, 7, 3, 31)
        )
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
        for url in self.non_existing_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)

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
        for url in self.non_existing_urls:
            response = self.client.get(url)
            self.assertNotEqual(response.content, 'NOTPROVIDED')
            self.assertNotEqual(response.content, '')

    def test_server_error(self):
        "The server_error view raises a 500 status"
        response = self.client.get('/server_error/')
        self.assertEqual(response.status_code, 500)

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
        Test that 404.html and 500.html templates are picked by their respective
        handler.
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

    @override_settings(DEFAULT_CONTENT_TYPE="text/xml")
    def test_default_content_type_is_text_html(self):
        """
        Content-Type of the default error responses is text/html. Refs #20822.
        """
        response = self.client.get('/raises400/')
        self.assertEqual(response['Content-Type'], 'text/html')

        response = self.client.get('/raises403/')
        self.assertEqual(response['Content-Type'], 'text/html')

        response = self.client.get('/non_existing_url/')
        self.assertEqual(response['Content-Type'], 'text/html')

        response = self.client.get('/server_error/')
        self.assertEqual(response['Content-Type'], 'text/html')
