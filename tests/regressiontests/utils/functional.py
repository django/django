from django.utils import unittest
from django.utils.functional import lazy


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
