from django.contrib.auth.tests.basic import BASIC_TESTS
from django.contrib.auth.tests.forms import FORM_TESTS, PasswordResetFormTestCase

__test__ = {
    'BASIC_TESTS': BASIC_TESTS,
    'PASSWORDRESET_TESTS': PasswordResetFormTestCase,
    'FORM_TESTS': FORM_TESTS,
}
