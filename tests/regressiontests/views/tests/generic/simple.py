# coding: utf-8

from django.test import TestCase

class RedirectToTest(TestCase):
    def test_redirect_to_returns_permanent_redirect(self):
        "simple.redirect_to returns a permanent redirect (301) by default"
        response = self.client.get('/views/simple/redirect_to/')
        self.assertEqual(response.status_code, 301)
        self.assertEqual('http://testserver/views/simple/target/', response['Location'])

    def test_redirect_to_can_return_a_temporary_redirect(self):
        "simple.redirect_to returns a temporary redirect (302) when explicitely asked to"
        response = self.client.get('/views/simple/redirect_to_temp/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual('http://testserver/views/simple/target/', response['Location'])

    def test_redirect_to_on_empty_url_returns_gone(self):
        "simple.redirect_to returns resource gone (410) when given a None url"
        response = self.client.get('/views/simple/redirect_to_none/')
        self.assertEqual(response.status_code, 410)

    def test_redirect_to_allows_formatted_url_string(self):
        "simple.redirect_to uses string interpolation on target url for keyword args"
        response = self.client.get('/views/simple/redirect_to_arg/42/')
        self.assertEqual(response.status_code, 301)
        self.assertEqual('http://testserver/views/simple/target_arg/42/', response['Location'])

    def test_redirect_to_allows_query_string_to_be_passed(self):
        "simple.redirect_to configured with query_string=True passes on any query string"
        # the default is to not forward the query string
        response = self.client.get('/views/simple/redirect_to/?param1=foo&param2=bar')
        self.assertEqual(response.status_code, 301)
        self.assertEqual('http://testserver/views/simple/target/', response['Location'])
        # views configured with query_string=True however passes the query string along
        response = self.client.get('/views/simple/redirect_to_query/?param1=foo&param2=bar')
        self.assertEqual(response.status_code, 301)
        self.assertEqual('http://testserver/views/simple/target/?param1=foo&param2=bar', response['Location'])
