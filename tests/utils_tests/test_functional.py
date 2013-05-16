from django.utils import unittest
from django.utils.functional import lazy, lazy_property, cached_property


class FunctionalTestCase(unittest.TestCase):
    def test_lazy(self):
        t = lazy(lambda: tuple(range(3)), list, tuple)
        for a, b in zip(t(), range(3)):
            self.assertEqual(a, b)

    def test_lazy_base_class(self):
        """Test that lazy also finds base class methods in the proxy object"""

        class Base(object):
            def base_method(self):
                pass

        class Klazz(Base):
            pass

        t = lazy(lambda: Klazz(), Klazz)()
        self.assertTrue('base_method' in dir(t))

    def test_lazy_property(self):

        class A(object):

            def _get_do(self):
                raise NotImplementedError
            def _set_do(self, value):
                raise NotImplementedError
            do = lazy_property(_get_do, _set_do)

        class B(A):
            def _get_do(self):
                return "DO IT"

        self.assertRaises(NotImplementedError, lambda: A().do)
        self.assertEqual(B().do, 'DO IT')

    def test_cached_property(self):
        """
        Test that cached_property caches its value,
        and that it behaves like a property
        """

        class A(object):

            @cached_property
            def value(self):
                return 1, object()

        a = A()

        # check that it is cached
        self.assertEqual(a.value, a.value)

        # check that it returns the right thing
        self.assertEqual(a.value[0], 1)

        # check that state isn't shared between instances
        a2 = A()
        self.assertNotEqual(a.value, a2.value)

        # check that it behaves like a property when there's no instance
        self.assertIsInstance(A.value, cached_property)
