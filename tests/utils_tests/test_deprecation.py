from django.test import SimpleTestCase
from django.utils.deprecation import CallableFalse, CallableTrue


class TestCallableBool(SimpleTestCase):
    def test_true(self):
        self.assertTrue(CallableTrue)
        self.assertEqual(CallableTrue, True)
        self.assertFalse(CallableTrue != True)  # noqa: E712
        self.assertNotEqual(CallableTrue, False)

    def test_false(self):
        self.assertFalse(CallableFalse)
        self.assertEqual(CallableFalse, False)
        self.assertFalse(CallableFalse != False)  # noqa: E712
        self.assertNotEqual(CallableFalse, True)

    def test_or(self):
        self.assertIs(CallableTrue | CallableTrue, True)
        self.assertIs(CallableTrue | CallableFalse, True)
        self.assertIs(CallableFalse | CallableTrue, True)
        self.assertIs(CallableFalse | CallableFalse, False)

        self.assertIs(CallableTrue | True, True)
        self.assertIs(CallableTrue | False, True)
        self.assertIs(CallableFalse | True, True)
        self.assertFalse(CallableFalse | False, False)

    def test_set_membership(self):
        self.assertIs(CallableTrue in {True}, True)
        self.assertIs(CallableFalse not in {True}, True)
