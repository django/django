import pickle
import datetime

from django.test import TestCase

from models import Group, Event, Happening


class PickleabilityTestCase(TestCase):
    def assert_pickles(self, qs):
        self.assertEqual(list(pickle.loads(pickle.dumps(qs))), list(qs))

    def test_related_field(self):
        g = Group.objects.create(name="Ponies Who Own Maybachs")
        self.assert_pickles(Event.objects.filter(group=g.id))

    def test_datetime_callable_default_all(self):
        self.assert_pickles(Happening.objects.all())

    def test_datetime_callable_default_filter(self):
        self.assert_pickles(Happening.objects.filter(when=datetime.datetime.now()))

    def test_lambda_as_default(self):
        self.assert_pickles(Happening.objects.filter(name="test"))

    def test_callable_as_default(self):
        self.assert_pickles(Happening.objects.filter(number=1))
