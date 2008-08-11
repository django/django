# -*- coding: utf-8 -*-

from xml.dom import minidom
from django.test import TestCase
from django.test.client import Client
from models import Entry

class SyndicationFeedTest(TestCase):
    fixtures = ['feeddata.json']

    def test_rss_feed(self):
        response = self.client.get('/syndication/feeds/rss/')
        doc = minidom.parseString(response.content)
        self.assertEqual(len(doc.getElementsByTagName('channel')), 1)
        self.assertEqual(len(doc.getElementsByTagName('item')), Entry.objects.count())
    
    def test_atom_feed(self):
        response = self.client.get('/syndication/feeds/atom/')
        doc = minidom.parseString(response.content)
        self.assertEqual(len(doc.getElementsByTagName('feed')), 1)
        self.assertEqual(len(doc.getElementsByTagName('entry')), Entry.objects.count())
    
    def test_complex_base_url(self):
        """
        Tests that that the base url for a complex feed doesn't raise a 500
        exception.
        """
        response = self.client.get('/syndication/feeds/complex/')
        self.assertEquals(response.status_code, 404)


