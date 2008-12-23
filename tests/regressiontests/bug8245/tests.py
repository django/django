from unittest import TestCase

from django.contrib import admin


class Bug8245Test(TestCase):
    """
    Test for bug #8245 - don't raise an AlreadyRegistered exception when using
    autodiscover() and an admin.py module contains an error.
    """

    def test_bug_8245(self):
        # The first time autodiscover is called, we should get our real error.
        try:
            admin.autodiscover()
        except Exception, e:
            self.failUnlessEqual(str(e), "Bad admin module")
        else:
            self.fail(
                'autodiscover should have raised a "Bad admin module" error.')
        # Calling autodiscover again should bail out early and not raise an
        # AlreadyRegistered error.
        admin.autodiscover()
