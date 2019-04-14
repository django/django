from django.test import SimpleTestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango40Warning
from django.utils.encoding import force_text, smart_text
from django.utils.functional import SimpleLazyObject
from django.utils.translation import gettext_lazy


@ignore_warnings(category=RemovedInDjango40Warning)
class TestDeprecatedEncodingUtils(SimpleTestCase):

    def test_force_text(self):
        s = SimpleLazyObject(lambda: 'x')
        self.assertIs(type(force_text(s)), str)

    def test_smart_text(self):
        class Test:
            def __str__(self):
                return 'ŠĐĆŽćžšđ'

        lazy_func = gettext_lazy('x')
        self.assertIs(smart_text(lazy_func), lazy_func)
        self.assertEqual(smart_text(Test()), '\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111')
        self.assertEqual(smart_text(1), '1')
        self.assertEqual(smart_text('foo'), 'foo')
