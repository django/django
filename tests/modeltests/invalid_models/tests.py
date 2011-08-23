import sys

from django.utils import unittest


class InvalidModelTestCase(unittest.TestCase):
    """Import an appliation with invalid models and test the exceptions."""

    def test_invalid_models(self):
        from django.core.management.validation import get_validation_errors
        from django.db.models.loading import load_app
        from cStringIO import StringIO

        try:
            module = load_app("modeltests.invalid_models.invalid_models")
        except Exception, e:
            self.fail('Unable to load invalid model module')

        # Make sure sys.stdout is not a tty so that we get errors without
        # coloring attached (makes matching the results easier). We restore
        # sys.stderr afterwards.
        orig_stdout = sys.stdout
        s = StringIO()
        sys.stdout = s
        count = get_validation_errors(s, module)
        sys.stdout = orig_stdout
        s.seek(0)
        error_log = s.read()
        actual = error_log.split('\n')
        expected = module.model_errors.split('\n')

        unexpected = [err for err in actual if err not in expected]
        missing = [err for err in expected if err not in actual]
        self.assertFalse(unexpected, "Unexpected Errors: " + '\n'.join(unexpected))
        self.assertFalse(missing, "Missing Errors: " + '\n'.join(missing))


