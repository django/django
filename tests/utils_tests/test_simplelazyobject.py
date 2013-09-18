from __future__ import unicode_literals

import copy
import pickle
import sys

from django.contrib.auth.models import User
from django.test import TestCase as DjangoTestCase
from django.utils import six
from django.utils.unittest import TestCase
from django.utils.functional import SimpleLazyObject, empty


class _ComplexObject(object):
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    if six.PY3:
        def __bytes__(self):
            return ("I am _ComplexObject(%r)" % self.name).encode("utf-8")

        def __str__(self):
            return self.name

    else:
        def __str__(self):
            return b"I am _ComplexObject(%r)" % str(self.name)

        def __unicode__(self):
            return self.name

    def __repr__(self):
        return "_ComplexObject(%r)" % self.name


complex_object = lambda: _ComplexObject("joe")


class TestUtilsSimpleLazyObject(TestCase):
    """
    Tests for SimpleLazyObject
    """
    # Note that concrete use cases for SimpleLazyObject are also found in the
    # auth context processor tests (unless the implementation of that function
    # is changed).

    def test_equality(self):
        self.assertEqual(complex_object(), SimpleLazyObject(complex_object))
        self.assertEqual(SimpleLazyObject(complex_object), complex_object())

    def test_hash(self):
        # hash() equality would not be true for many objects, but it should be
        # for _ComplexObject
        self.assertEqual(hash(complex_object()),
                         hash(SimpleLazyObject(complex_object)))

    def test_repr(self):
        # First, for an unevaluated SimpleLazyObject
        x = SimpleLazyObject(complex_object)
        # __repr__ contains __repr__ of setup function and does not evaluate
        # the SimpleLazyObject
        self.assertEqual("<SimpleLazyObject: %r>" % complex_object, repr(x))
        self.assertEqual(empty, x._wrapped)

        # Second, for an evaluated SimpleLazyObject
        name = x.name  # evaluate
        self.assertIsInstance(x._wrapped, _ComplexObject)
        # __repr__ contains __repr__ of wrapped object
        self.assertEqual("<SimpleLazyObject: %r>" % x._wrapped, repr(x))

    def test_bytes(self):
        self.assertEqual(b"I am _ComplexObject('joe')",
                bytes(SimpleLazyObject(complex_object)))

    def test_text(self):
        self.assertEqual("joe", six.text_type(SimpleLazyObject(complex_object)))

    def test_class(self):
        # This is important for classes that use __class__ in things like
        # equality tests.
        self.assertEqual(_ComplexObject, SimpleLazyObject(complex_object).__class__)

    def test_deepcopy(self):
        # Check that we *can* do deep copy, and that it returns the right
        # objects.

        # First, for an unevaluated SimpleLazyObject
        s = SimpleLazyObject(complex_object)
        self.assertIs(s._wrapped, empty)
        s2 = copy.deepcopy(s)
        # something has gone wrong is s is evaluated
        self.assertIs(s._wrapped, empty)
        self.assertEqual(s2, complex_object())

        # Second, for an evaluated SimpleLazyObject
        name = s.name  # evaluate
        self.assertIsNot(s._wrapped, empty)
        s3 = copy.deepcopy(s)
        self.assertEqual(s3, complex_object())

    def test_none(self):
        i = [0]

        def f():
            i[0] += 1
            return None

        x = SimpleLazyObject(f)
        self.assertEqual(str(x), "None")
        self.assertEqual(i, [1])
        self.assertEqual(str(x), "None")
        self.assertEqual(i, [1])

    def test_bool(self):
        x = SimpleLazyObject(lambda: 3)
        self.assertTrue(x)
        x = SimpleLazyObject(lambda: 0)
        self.assertFalse(x)

    def test_pickle_complex(self):
        # See ticket #16563
        x = SimpleLazyObject(complex_object)
        pickled = pickle.dumps(x)
        unpickled = pickle.loads(pickled)
        self.assertEqual(unpickled, x)
        self.assertEqual(six.text_type(unpickled), six.text_type(x))
        self.assertEqual(unpickled.name, x.name)

    def test_dict(self):
        # See ticket #18447
        lazydict = SimpleLazyObject(lambda: {'one': 1})
        self.assertEqual(lazydict['one'], 1)
        lazydict['one'] = -1
        self.assertEqual(lazydict['one'], -1)
        del lazydict['one']
        with self.assertRaises(KeyError):
            lazydict['one']

    def test_trace(self):
        # See ticket #19456
        old_trace_func = sys.gettrace()
        try:
            def trace_func(frame, event, arg):
                frame.f_locals['self'].__class__
                if old_trace_func is not None:
                    old_trace_func(frame, event, arg)
            sys.settrace(trace_func)
            SimpleLazyObject(None)
        finally:
            sys.settrace(old_trace_func)

    def test_not_equal(self):
        lazy1 = SimpleLazyObject(lambda: 2)
        lazy2 = SimpleLazyObject(lambda: 2)
        lazy3 = SimpleLazyObject(lambda: 3)
        self.assertEqual(lazy1, lazy2)
        self.assertNotEqual(lazy1, lazy3)
        self.assertTrue(lazy1 != lazy3)
        self.assertFalse(lazy1 != lazy2)


class TestUtilsSimpleLazyObjectDjangoTestCase(DjangoTestCase):

    def test_pickle_py2_regression(self):
        # See ticket #20212
        user = User.objects.create_user('johndoe', 'john@example.com', 'pass')
        x = SimpleLazyObject(lambda: user)

        # This would fail with "TypeError: can't pickle instancemethod objects",
        # only on Python 2.X.
        pickled = pickle.dumps(x)

        # Try the variant protocol levels.
        pickled = pickle.dumps(x, 0)
        pickled = pickle.dumps(x, 1)
        pickled = pickle.dumps(x, 2)

        if six.PY2:
            import cPickle

            # This would fail with "TypeError: expected string or Unicode object, NoneType found".
            pickled = cPickle.dumps(x)
