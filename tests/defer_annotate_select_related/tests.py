from django.db.models import Count
from django.test import TestCase
from models import *

class DeferAnnotateSelectRelatedTest(TestCase):
    def test(self):
        location = Location.objects.create()
        request = Request.objects.create(location=location)
        self.assertIsInstance(list(Request.objects
            .annotate(Count('items')).select_related('profile', 'location')
            .only('profile', 'location')), list)
        self.assertIsInstance(list(Request.objects
            .annotate(Count('items')).select_related('profile', 'location')
            .only('profile__profile1', 'location__location1')), list)
        self.assertIsInstance(list(Request.objects
            .annotate(Count('items')).select_related('profile', 'location')
            .defer('request1', 'request2', 'request3', 'request4')), list)
