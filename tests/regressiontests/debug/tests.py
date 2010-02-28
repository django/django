from django.test import TestCase
from django.conf import settings
from django.core.urlresolvers import reverse

from regressiontests.debug import BrokenException, except_args

class ExceptionTest(TestCase):
    urls = 'regressiontests.debug.urls'

    def setUp(self):
        self.old_debug = settings.DEBUG
        settings.DEBUG = True

    def tearDown(self):
        settings.DEBUG = self.old_debug

    def test_view_exceptions(self):
        for n in range(len(except_args)):
            self.assertRaises(BrokenException, self.client.get,
                reverse('view_exception', args=(n,)))

