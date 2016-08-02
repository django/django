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
