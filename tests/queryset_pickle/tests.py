from __future__ import absolute_import

import pickle
import datetime

from django.test import TestCase

from .models import Group, Event, Happening


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

    def test_standalone_method_as_default(self):
        self.assert_pickles(Happening.objects.filter(number1=1))

    def test_staticmethod_as_default(self):
        self.assert_pickles(Happening.objects.filter(number2=1))

    def test_classmethod_as_default(self):
        self.assert_pickles(Happening.objects.filter(number3=1))

    def test_membermethod_as_default(self):
        self.assert_pickles(Happening.objects.filter(number4=1))

    def test_doesnotexist_exception(self):
        # Ticket #17776
        original = Event.DoesNotExist("Doesn't exist")
        unpickled = pickle.loads(pickle.dumps(original))

        # Exceptions are not equal to equivalent instances of themselves, so
        # can't just use assertEqual(original, unpickled)
        self.assertEqual(original.__class__, unpickled.__class__)
        self.assertEqual(original.args, unpickled.args)
