from django.contrib.auth.tests.basic import BASIC_TESTS, PasswordResetTest
from django.contrib.auth.tests.forms import FORM_TESTS

__test__ = {
    'BASIC_TESTS': BASIC_TESTS,
    'PASSWORDRESET_TESTS': PasswordResetTest,
    'FORM_TESTS': FORM_TESTS,
}
