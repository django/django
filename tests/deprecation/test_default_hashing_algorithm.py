import sys
from types import ModuleType

from django.conf import (
    DEFAULT_HASHING_ALGORITHM_DEPRECATED_MSG, Settings, settings,
)
from django.core.checks.security import base as security_base
from django.test import TestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango40Warning


class DefaultHashingAlgorithmDeprecationTests(TestCase):
    msg = DEFAULT_HASHING_ALGORITHM_DEPRECATED_MSG

    def test_override_settings_warning(self):
        with self.assertRaisesMessage(RemovedInDjango40Warning, self.msg):
            with self.settings(DEFAULT_HASHING_ALGORITHM='sha1'):
                pass

    def test_settings_init_warning(self):
        settings_module = ModuleType('fake_settings_module')
        settings_module.SECRET_KEY = 'foo'
        settings_module.DEFAULT_HASHING_ALGORITHM = 'sha1'
        sys.modules['fake_settings_module'] = settings_module
        try:
            with self.assertRaisesMessage(RemovedInDjango40Warning, self.msg):
                Settings('fake_settings_module')
        finally:
            del sys.modules['fake_settings_module']

    def test_access(self):
        # Warning is not raised on access.
        self.assertEqual(settings.DEFAULT_HASHING_ALGORITHM, 'sha256')

    @ignore_warnings(category=RemovedInDjango40Warning)
    def test_system_check_invalid_value(self):
        tests = [
            None,
            256,
            'invalid',
            'md5',
            'sha512',
        ]
        for value in tests:
            with self.subTest(value=value), self.settings(DEFAULT_HASHING_ALGORITHM=value):
                self.assertEqual(
                    security_base.check_default_hashing_algorithm(None),
                    [security_base.E100],
                )

    @ignore_warnings(category=RemovedInDjango40Warning)
    def test_system_check_valid_value(self):
        for value in ['sha1', 'sha256']:
            with self.subTest(value=value), self.settings(DEFAULT_HASHING_ALGORITHM=value):
                self.assertEqual(security_base.check_default_hashing_algorithm(None), [])
