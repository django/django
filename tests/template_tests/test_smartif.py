from django.template.smartif import IfParser
from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango41Warning


class SmartIfTests(SimpleTestCase):

    def assertCalcEqual(self, expected, tokens):
        self.assertEqual(expected, IfParser(tokens).parse().eval({}))

    # We only test things here that are difficult to test elsewhere
    # Many other tests are found in the main tests for builtin template tags
    # Test parsing via the printed parse tree
    def test_not(self):
        var = IfParser(["not", False]).parse()
        self.assertEqual("(not (literal False))", repr(var))
        self.assertTrue(var.eval({}))

        self.assertFalse(IfParser(["not", True]).parse().eval({}))

    def test_or(self):
        var = IfParser([True, "or", False]).parse()
        self.assertEqual("(or (literal True) (literal False))", repr(var))
        self.assertTrue(var.eval({}))

    def test_in(self):
        list_ = [1, 2, 3]
        self.assertCalcEqual(True, [1, 'in', list_])
        self.assertCalcEqual(False, [None, 'in', list_])
        msg = (
            "Evaluating an {% if %} in a template raised an exception. In "
            "Django 4.1, this exception will be raised rather than silenced. "
            "The exception was:\n"
            "TypeError: argument of type 'NoneType' is not iterable"
        )
        # TODO: Change to assertRaisesMessage after the deprecation period.
        with self.assertWarnsMessage(RemovedInDjango41Warning, msg):
            self.assertCalcEqual(False, [1, 'in', None])

    def test_not_in(self):
        list_ = [1, 2, 3]
        self.assertCalcEqual(False, [1, 'not', 'in', list_])
        self.assertCalcEqual(True, [4, 'not', 'in', list_])
        self.assertCalcEqual(True, [None, 'not', 'in', list_])
        msg = (
            "Evaluating an {% if %} in a template raised an exception. In "
            "Django 4.1, this exception will be raised rather than silenced. "
            "The exception was:\n"
            "TypeError: argument of type 'NoneType' is not iterable"
        )
        # TODO: Change to assertRaisesMessage after the deprecation period.
        with self.assertWarnsMessage(RemovedInDjango41Warning, msg):
            self.assertCalcEqual(False, [1, 'not', 'in', None])

    def test_precedence(self):
        # (False and False) or True == True   <- we want this one, like Python
        # False and (False or True) == False
        self.assertCalcEqual(True, [False, 'and', False, 'or', True])

        # True or (False and False) == True   <- we want this one, like Python
        # (True or False) and False == False
        self.assertCalcEqual(True, [True, 'or', False, 'and', False])

        # (1 or 1) == 2  -> False
        # 1 or (1 == 2)  -> True   <- we want this one
        self.assertCalcEqual(True, [1, 'or', 1, '==', 2])

        self.assertCalcEqual(True, [True, '==', True, 'or', True, '==', False])

        self.assertEqual("(or (and (== (literal 1) (literal 2)) (literal 3)) (literal 4))",
                         repr(IfParser([1, '==', 2, 'and', 3, 'or', 4]).parse()))
