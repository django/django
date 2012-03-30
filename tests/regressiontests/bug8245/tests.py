from django.contrib import admin
from django.utils.unittest import TestCase


class Bug8245Test(TestCase):
    """
    Test for bug #8245 - don't raise an AlreadyRegistered exception when using
    autodiscover() and an admin.py module contains an error.
    """
    def test_bug_8245(self):
        # The first time autodiscover is called, we should get our real error.
        with self.assertRaises(Exception) as cm:
            admin.autodiscover()
        self.assertEqual(str(cm.exception), "Bad admin module")

        # Calling autodiscover again should raise the very same error it did
        # the first time, not an AlreadyRegistered error.
        with self.assertRaises(Exception) as cm:
            admin.autodiscover()
        self.assertEqual(str(cm.exception), "Bad admin module")
