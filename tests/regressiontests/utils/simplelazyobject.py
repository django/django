import copy
import pickle

from django.utils.unittest import TestCase
from django.utils.functional import SimpleLazyObject, empty


class _ComplexObject(object):
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return "I am _ComplexObject(%r)" % self.name

    def __unicode__(self):
        return unicode(self.name)

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
        # For debugging, it will really confuse things if there is no clue that
        # SimpleLazyObject is actually a proxy object. So we don't
        # proxy __repr__
        self.assertTrue("SimpleLazyObject" in repr(SimpleLazyObject(complex_object)))

    def test_str(self):
        self.assertEqual("I am _ComplexObject('joe')", str(SimpleLazyObject(complex_object)))

    def test_unicode(self):
        self.assertEqual(u"joe", unicode(SimpleLazyObject(complex_object)))

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
        name = s.name # evaluate
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
        self.assertEqual(unicode(unpickled), unicode(x))
        self.assertEqual(unpickled.name, x.name)
