import warnings

from django.dispatch import Signal
from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango40Warning


class SignalDeprecationTests(SimpleTestCase):
    def test_providing_args_warning(self):
        msg = (
            'The providing_args argument is deprecated. As it is purely '
            'documentational, it has no replacement. If you rely on this '
            'argument as documentation, you can move the text to a code '
            'comment or docstring.'
        )
        with self.assertWarnsMessage(RemovedInDjango40Warning, msg):
            Signal(providing_args=['arg1', 'arg2'])

    def test_without_providing_args_does_not_warn(self):
        with warnings.catch_warnings(record=True) as recorded:
            Signal()
        self.assertEqual(len(recorded), 0)
