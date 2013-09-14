from __future__ import absolute_import

import pickle
import datetime

from django.db import models
from django.test import TestCase

from .models import Group, Event, Happening, Container, M2MModel


class PickleabilityTestCase(TestCase):
    def setUp(self):
        Happening.objects.create() # make sure the defaults are working (#20158)

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

    def test_model_pickle(self):
        """
        Test that a model not defined on module level is pickleable.
        """
        original = Container.SomeModel(pk=1)
        dumped = pickle.dumps(original)
        reloaded = pickle.loads(dumped)
        self.assertEqual(original, reloaded)
        # Also, deferred dynamic model works
        Container.SomeModel.objects.create(somefield=1)
        original = Container.SomeModel.objects.defer('somefield')[0]
        dumped = pickle.dumps(original)
        reloaded = pickle.loads(dumped)
        self.assertEqual(original, reloaded)
        self.assertEqual(original.somefield, reloaded.somefield)

    def test_model_pickle_m2m(self):
        """
        Test intentionally the automatically created through model.
        """
        m1 = M2MModel.objects.create()
        g1 = Group.objects.create(name='foof')
        m1.groups.add(g1)
        m2m_through = M2MModel._meta.get_field_by_name('groups')[0].rel.through
        original = m2m_through.objects.get()
        dumped = pickle.dumps(original)
        reloaded = pickle.loads(dumped)
        self.assertEqual(original, reloaded)

    def test_model_pickle_dynamic(self):
        class Meta:
            proxy = True
        dynclass = type("DynamicEventSubclass", (Event, ),
                        {'Meta': Meta, '__module__': Event.__module__})
        original = dynclass(pk=1)
        dumped = pickle.dumps(original)
        reloaded = pickle.loads(dumped)
        self.assertEqual(original, reloaded)
        self.assertIs(reloaded.__class__, dynclass)

    def test_pickle_prefetch_related_idempotence(self):
        g = Group.objects.create(name='foo')
        groups = Group.objects.prefetch_related('event_set')

        # First pickling
        groups = pickle.loads(pickle.dumps(groups))
        self.assertQuerysetEqual(groups, [g], lambda x: x)

        # Second pickling
        groups = pickle.loads(pickle.dumps(groups))
        self.assertQuerysetEqual(groups, [g], lambda x: x)
