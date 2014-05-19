"""Tests for ``django/utils/formats.py``."""
from django.test import TestCase
from django.utils.formats import iter_format_modules


class IterFormatModulesTestCase(TestCase):
    """Tests for the ``iter_format_modules`` method."""
    longMessage = True

    def test_returns_correct_default(self):
        """
        Should return default module when FORMAT_MODULE_PATH is not set.
        """
        result = list(iter_format_modules('en'))
        self.assertEqual(len(result), 1, msg=(
            "Should return only Django's default formats module."))
        self.assertEqual(
            result[0].__name__, 'django.conf.locale.en.formats', msg=(
                'Should have added the language to the module path'))

    def test_with_setting_as_basestring(self):
        """
        Before ticket #20477 FORMAT_MODULE_PATH was supposed to be a string.

        This test ensures backwards compatibility.
        """
        with self.settings(
                FORMAT_MODULE_PATH='utils_tests.test_module.formats'):
            result = list(iter_format_modules('en'))
            self.assertEqual(len(result), 2, msg=(
                'Should return both, the default value and the one from the'
                ' setting'))
            self.assertEqual(
                result[0].__name__,
                'utils_tests.test_module.formats.en.formats',
                msg=('Should return the module from the setting first and'
                     ' should have added the language to the module path'))

    def test_with_setting_as_list_of_strings(self):
        """
        After ticket #20477 FORMAT_MODULE_PATH can also be a list of strings.

        This tests verifies the new functionality.
        """
        FORMAT_MODULE_PATH = [
            'utils_tests.test_module.formats',
            'utils_tests.test_module.formats2',
        ]
        with self.settings(
                FORMAT_MODULE_PATH=FORMAT_MODULE_PATH):
            result = list(iter_format_modules('en'))
            self.assertEqual(len(result), 3, msg=(
                'Should return the default value and the two values from the'
                ' setting'))
            self.assertEqual(
                result[0].__name__,
                'utils_tests.test_module.formats.en.formats',
                msg=('Should return the values from the setting and add the'
                     ' language to the module path'))
