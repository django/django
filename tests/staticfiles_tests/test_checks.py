from unittest import mock

from django.conf import settings
from django.contrib.staticfiles.checks import check_finders
from django.contrib.staticfiles.finders import BaseFinder
from django.core.checks import Error
from django.test import SimpleTestCase, override_settings


class FindersCheckTests(SimpleTestCase):

    def test_base_finder_check_not_implemented(self):
        finder = BaseFinder()
        msg = 'subclasses may provide a check() method to verify the finder is configured correctly.'
        with self.assertRaisesMessage(NotImplementedError, msg):
            finder.check()

    def test_check_finders(self):
        """check_finders() concatenates all errors."""
        error1 = Error('1')
        error2 = Error('2')
        error3 = Error('3')

        def get_finders():
            class Finder1(BaseFinder):
                def check(self, **kwargs):
                    return [error1]

            class Finder2(BaseFinder):
                def check(self, **kwargs):
                    return []

            class Finder3(BaseFinder):
                def check(self, **kwargs):
                    return [error2, error3]

            class Finder4(BaseFinder):
                pass

            return [Finder1(), Finder2(), Finder3(), Finder4()]

        with mock.patch('django.contrib.staticfiles.checks.get_finders', get_finders):
            errors = check_finders(None)
            self.assertEqual(errors, [error1, error2, error3])

    def test_no_errors_with_test_settings(self):
        self.assertEqual(check_finders(None), [])

    @override_settings(STATICFILES_DIRS='a string')
    def test_dirs_not_tuple_or_list(self):
        self.assertEqual(check_finders(None), [
            Error(
                'The STATICFILES_DIRS setting is not a tuple or list.',
                hint='Perhaps you forgot a trailing comma?',
                id='staticfiles.E001',
            )
        ])

    @override_settings(STATICFILES_DIRS=['/fake/path', settings.STATIC_ROOT])
    def test_dirs_contains_static_root(self):
        self.assertEqual(check_finders(None), [
            Error(
                'The STATICFILES_DIRS setting should not contain the '
                'STATIC_ROOT setting.',
                id='staticfiles.E002',
            )
        ])

    @override_settings(STATICFILES_DIRS=[('prefix', settings.STATIC_ROOT)])
    def test_dirs_contains_static_root_in_tuple(self):
        self.assertEqual(check_finders(None), [
            Error(
                'The STATICFILES_DIRS setting should not contain the '
                'STATIC_ROOT setting.',
                id='staticfiles.E002',
            )
        ])
