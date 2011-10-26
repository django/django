# coding: utf-8
import warnings

from django.test import TestCase

class RedirectToTest(TestCase):
    urls = 'regressiontests.views.generic_urls'

    def setUp(self):
        self.save_warnings_state()
        warnings.filterwarnings('ignore', category=DeprecationWarning,
                                module='django.views.generic.simple')

    def tearDown(self):
        self.restore_warnings_state()

    def test_redirect_to_returns_permanent_redirect(self):
        "simple.redirect_to returns a permanent redirect (301) by default"
        response = self.client.get('/simple/redirect_to/')
        self.assertEqual(response.status_code, 301)
        self.assertEqual('http://testserver/simple/target/', response['Location'])

    def test_redirect_to_can_return_a_temporary_redirect(self):
        "simple.redirect_to returns a temporary redirect (302) when explicitely asked to"
        response = self.client.get('/simple/redirect_to_temp/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual('http://testserver/simple/target/', response['Location'])

    def test_redirect_to_on_empty_url_returns_gone(self):
        "simple.redirect_to returns resource gone (410) when given a None url"
        response = self.client.get('/simple/redirect_to_none/')
        self.assertEqual(response.status_code, 410)

    def test_redirect_to_allows_formatted_url_string(self):
        "simple.redirect_to uses string interpolation on target url for keyword args"
        response = self.client.get('/simple/redirect_to_arg/42/')
        self.assertEqual(response.status_code, 301)
        self.assertEqual('http://testserver/simple/target_arg/42/', response['Location'])

    def test_redirect_to_allows_query_string_to_be_passed(self):
        "simple.redirect_to configured with query_string=True passes on any query string"
        # the default is to not forward the query string
        response = self.client.get('/simple/redirect_to/?param1=foo&param2=bar')
        self.assertEqual(response.status_code, 301)
        self.assertEqual('http://testserver/simple/target/', response['Location'])
        # views configured with query_string=True however passes the query string along
        response = self.client.get('/simple/redirect_to_query/?param1=foo&param2=bar')
        self.assertEqual(response.status_code, 301)
        self.assertEqual('http://testserver/simple/target/?param1=foo&param2=bar', response['Location'])

        # Confirm that the contents of the query string are not subject to
        # string interpolation (Refs #17111):
        response = self.client.get('/simple/redirect_to_query/?param1=foo&param2=hist%C3%B3ria')
        self.assertEqual(response.status_code, 301)
        self.assertEqual('http://testserver/simple/target/?param1=foo&param2=hist%C3%B3ria', response['Location'])
        response = self.client.get('/simple/redirect_to_arg_and_query/99/?param1=foo&param2=hist%C3%B3ria')
        self.assertEqual(response.status_code, 301)
        self.assertEqual('http://testserver/simple/target_arg/99/?param1=foo&param2=hist%C3%B3ria', response['Location'])

    def test_redirect_to_when_meta_contains_no_query_string(self):
        "regression for #16705"
        # we can't use self.client.get because it always sets QUERY_STRING
        response = self.client.request(PATH_INFO='/simple/redirect_to/')
        self.assertEqual(response.status_code, 301)
