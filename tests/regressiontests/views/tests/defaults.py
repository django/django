from os import path

from django.conf import settings
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

from regressiontests.views.models import Author, Article

class DefaultsTests(TestCase):
    """Test django views in django/views/defaults.py"""
    fixtures = ['testdata.json']

    def test_shortcut_with_absolute_url(self):
        "Can view a shortcut for an Author object that has a get_absolute_url method"
        for obj in Author.objects.all():
            short_url = '/views/shortcut/%s/%s/' % (ContentType.objects.get_for_model(Author).id, obj.pk)
            response = self.client.get(short_url)
            self.assertRedirects(response, 'http://testserver%s' % obj.get_absolute_url(), 
                                 status_code=302, target_status_code=404)

    def test_shortcut_no_absolute_url(self):
        "Shortcuts for an object that has no get_absolute_url method raises 404"
        for obj in Article.objects.all():
            short_url = '/views/shortcut/%s/%s/' % (ContentType.objects.get_for_model(Article).id, obj.pk)
            response = self.client.get(short_url)
            self.assertEquals(response.status_code, 404)

    def test_wrong_type_pk(self):
        short_url = '/views/shortcut/%s/%s/' % (ContentType.objects.get_for_model(Author).id, 'nobody/expects')
        response = self.client.get(short_url)
        self.assertEquals(response.status_code, 404)

    def test_shortcut_bad_pk(self):
        short_url = '/views/shortcut/%s/%s/' % (ContentType.objects.get_for_model(Author).id, '4242424242')
        response = self.client.get(short_url)
        self.assertEquals(response.status_code, 404)

    def test_nonint_content_type(self):
        an_author = Author.objects.all()[0]
        short_url = '/views/shortcut/%s/%s/' % ('spam', an_author.pk)
        response = self.client.get(short_url)
        self.assertEquals(response.status_code, 404)

    def test_bad_content_type(self):
        an_author = Author.objects.all()[0]
        short_url = '/views/shortcut/%s/%s/' % (4242424242, an_author.pk)
        response = self.client.get(short_url)
        self.assertEquals(response.status_code, 404)

    def test_page_not_found(self):
        "A 404 status is returned by the page_not_found view"
        non_existing_urls = ['/views/non_existing_url/', # this is in urls.py
                             '/views/other_non_existing_url/'] # this NOT in urls.py
        for url in non_existing_urls:
            response = self.client.get(url)
            self.assertEquals(response.status_code, 404)

    def test_server_error(self):
        "The server_error view raises a 500 status"
        response = self.client.get('/views/server_error/')
        self.assertEquals(response.status_code, 500)
