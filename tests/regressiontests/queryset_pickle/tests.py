from __future__ import absolute_import

import pickle
import datetime

from django.test import TestCase

from .models import Group, Event, Happening, Person, Post
from django.contrib.auth.models import AnonymousUser


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

    def test_pickle_m2m_prefetch_related(self):
        bob = Person(name="Bob")
        bob.save()
        people = Person.objects.prefetch_related('socialprofile_set')
        dumped = pickle.dumps(people)
        people = pickle.loads(dumped)
        self.assertQuerysetEqual(
            people, [bob], lambda x: x)

    def test_pickle_field_default_prefetch_related(self):
        p1 = Post.objects.create()
        posts = Post.objects.prefetch_related('materials')
        dumped = pickle.dumps(posts)
        posts = pickle.loads(dumped)
        self.assertQuerysetEqual(
            posts, [p1], lambda x: x)

    def test_pickle_emptyqs(self):
        u = AnonymousUser()
        # Use AnonymousUser, as AnonymousUser.groups has qs.model = None
        empty = u.groups.all()
        dumped = pickle.dumps(empty)
        empty = pickle.loads(dumped)
        self.assertQuerysetEqual(
            empty, [])

    def test_pickle_prefetch_related_idempotence(self):
        p = Post.objects.create()
        posts = Post.objects.prefetch_related('materials')

        # First pickling
        posts = pickle.loads(pickle.dumps(posts))
        self.assertQuerysetEqual(posts, [p], lambda x: x)

        # Second pickling
        posts = pickle.loads(pickle.dumps(posts))
        self.assertQuerysetEqual(posts, [p], lambda x: x)
