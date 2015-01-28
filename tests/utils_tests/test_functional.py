import unittest

from django.utils.functional import cached_property, lazy, lazy_property


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
        self.assertIn('base_method', dir(t))

    def test_lazy_base_class_override(self):
        """Test that lazy finds the correct (overridden) method implementation"""

        class Base(object):
            def method(self):
                return 'Base'

        class Klazz(Base):
            def method(self):
                return 'Klazz'

        t = lazy(lambda: Klazz(), Base)()
        self.assertEqual(t.method(), 'Klazz')

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
                """Here is the docstring..."""
                return 1, object()

            def other_value(self):
                return 1

            other = cached_property(other_value, name='other')

        # docstring should be preserved
        self.assertEqual(A.value.__doc__, "Here is the docstring...")

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

        # check that overriding name works
        self.assertEqual(a.other, 1)
        self.assertTrue(callable(a.other_value))

    def test_lazy_equality(self):
        """
        Tests that == and != work correctly for Promises.
        """

        lazy_a = lazy(lambda: 4, int)
        lazy_b = lazy(lambda: 4, int)
        lazy_c = lazy(lambda: 5, int)

        self.assertEqual(lazy_a(), lazy_b())
        self.assertNotEqual(lazy_b(), lazy_c())
