import os
import sys
import unittest
import warnings
from types import ModuleType
from unittest import mock

from django.conf import ENVIRONMENT_VARIABLE, LazySettings, Settings, settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest
from django.test import (
    SimpleTestCase, TestCase, TransactionTestCase, modify_settings,
    override_settings, signals,
)
from django.test.utils import requires_tz_support


@modify_settings(ITEMS={
    'prepend': ['b'],
    'append': ['d'],
    'remove': ['a', 'e']
})
@override_settings(ITEMS=['a', 'c', 'e'], ITEMS_OUTER=[1, 2, 3], TEST='override', TEST_OUTER='outer')
class FullyDecoratedTranTestCase(TransactionTestCase):

    available_apps = []

    def test_override(self):
        self.assertEqual(settings.ITEMS, ['b', 'c', 'd'])
        self.assertEqual(settings.ITEMS_OUTER, [1, 2, 3])
        self.assertEqual(settings.TEST, 'override')
        self.assertEqual(settings.TEST_OUTER, 'outer')

    @modify_settings(ITEMS={
        'append': ['e', 'f'],
        'prepend': ['a'],
        'remove': ['d', 'c'],
    })
    def test_method_list_override(self):
        self.assertEqual(settings.ITEMS, ['a', 'b', 'e', 'f'])
        self.assertEqual(settings.ITEMS_OUTER, [1, 2, 3])

    @modify_settings(ITEMS={
        'append': ['b'],
        'prepend': ['d'],
        'remove': ['a', 'c', 'e'],
    })
    def test_method_list_override_no_ops(self):
        self.assertEqual(settings.ITEMS, ['b', 'd'])

    @modify_settings(ITEMS={
        'append': 'e',
        'prepend': 'a',
        'remove': 'c',
    })
    def test_method_list_override_strings(self):
        self.assertEqual(settings.ITEMS, ['a', 'b', 'd', 'e'])

    @modify_settings(ITEMS={'remove': ['b', 'd']})
    @modify_settings(ITEMS={'append': ['b'], 'prepend': ['d']})
    def test_method_list_override_nested_order(self):
        self.assertEqual(settings.ITEMS, ['d', 'c', 'b'])

    @override_settings(TEST='override2')
    def test_method_override(self):
        self.assertEqual(settings.TEST, 'override2')
        self.assertEqual(settings.TEST_OUTER, 'outer')

    def test_decorated_testcase_name(self):
        self.assertEqual(FullyDecoratedTranTestCase.__name__, 'FullyDecoratedTranTestCase')

    def test_decorated_testcase_module(self):
        self.assertEqual(FullyDecoratedTranTestCase.__module__, __name__)


@modify_settings(ITEMS={
    'prepend': ['b'],
    'append': ['d'],
    'remove': ['a', 'e']
})
@override_settings(ITEMS=['a', 'c', 'e'], TEST='override')
class FullyDecoratedTestCase(TestCase):

    def test_override(self):
        self.assertEqual(settings.ITEMS, ['b', 'c', 'd'])
        self.assertEqual(settings.TEST, 'override')

    @modify_settings(ITEMS={
        'append': 'e',
        'prepend': 'a',
        'remove': 'c',
    })
    @override_settings(TEST='override2')
    def test_method_override(self):
        self.assertEqual(settings.ITEMS, ['a', 'b', 'd', 'e'])
        self.assertEqual(settings.TEST, 'override2')


class ClassDecoratedTestCaseSuper(TestCase):
    """
    Dummy class for testing max recursion error in child class call to
    super().  Refs #17011.
    """
    def test_max_recursion_error(self):
        pass


@override_settings(TEST='override')
class ClassDecoratedTestCase(ClassDecoratedTestCaseSuper):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.foo = getattr(settings, 'TEST', 'BUG')

    def test_override(self):
        self.assertEqual(settings.TEST, 'override')

    def test_setupclass_override(self):
        """Settings are overridden within setUpClass (#21281)."""
        self.assertEqual(self.foo, 'override')

    @override_settings(TEST='override2')
    def test_method_override(self):
        self.assertEqual(settings.TEST, 'override2')

    def test_max_recursion_error(self):
        """
        Overriding a method on a super class and then calling that method on
        the super class should not trigger infinite recursion. See #17011.
        """
        super().test_max_recursion_error()


@modify_settings(ITEMS={'append': 'mother'})
@override_settings(ITEMS=['father'], TEST='override-parent')
class ParentDecoratedTestCase(TestCase):
    pass


@modify_settings(ITEMS={'append': ['child']})
@override_settings(TEST='override-child')
class ChildDecoratedTestCase(ParentDecoratedTestCase):
    def test_override_settings_inheritance(self):
        self.assertEqual(settings.ITEMS, ['father', 'mother', 'child'])
        self.assertEqual(settings.TEST, 'override-child')


class SettingsTests(SimpleTestCase):
    def setUp(self):
        self.testvalue = None
        signals.setting_changed.connect(self.signal_callback)

    def tearDown(self):
        signals.setting_changed.disconnect(self.signal_callback)

    def signal_callback(self, sender, setting, value, **kwargs):
        if setting == 'TEST':
            self.testvalue = value

    def test_override(self):
        settings.TEST = 'test'
        self.assertEqual('test', settings.TEST)
        with self.settings(TEST='override'):
            self.assertEqual('override', settings.TEST)
        self.assertEqual('test', settings.TEST)
        del settings.TEST

    def test_override_change(self):
        settings.TEST = 'test'
        self.assertEqual('test', settings.TEST)
        with self.settings(TEST='override'):
            self.assertEqual('override', settings.TEST)
            settings.TEST = 'test2'
        self.assertEqual('test', settings.TEST)
        del settings.TEST

    def test_override_doesnt_leak(self):
        with self.assertRaises(AttributeError):
            getattr(settings, 'TEST')
        with self.settings(TEST='override'):
            self.assertEqual('override', settings.TEST)
            settings.TEST = 'test'
        with self.assertRaises(AttributeError):
            getattr(settings, 'TEST')

    @override_settings(TEST='override')
    def test_decorator(self):
        self.assertEqual('override', settings.TEST)

    def test_context_manager(self):
        with self.assertRaises(AttributeError):
            getattr(settings, 'TEST')
        override = override_settings(TEST='override')
        with self.assertRaises(AttributeError):
            getattr(settings, 'TEST')
        override.enable()
        self.assertEqual('override', settings.TEST)
        override.disable()
        with self.assertRaises(AttributeError):
            getattr(settings, 'TEST')

    def test_class_decorator(self):
        # SimpleTestCase can be decorated by override_settings, but not ut.TestCase
        class SimpleTestCaseSubclass(SimpleTestCase):
            pass

        class UnittestTestCaseSubclass(unittest.TestCase):
            pass

        decorated = override_settings(TEST='override')(SimpleTestCaseSubclass)
        self.assertIsInstance(decorated, type)
        self.assertTrue(issubclass(decorated, SimpleTestCase))

        with self.assertRaisesMessage(Exception, "Only subclasses of Django SimpleTestCase"):
            decorated = override_settings(TEST='override')(UnittestTestCaseSubclass)

    def test_signal_callback_context_manager(self):
        with self.assertRaises(AttributeError):
            getattr(settings, 'TEST')
        with self.settings(TEST='override'):
            self.assertEqual(self.testvalue, 'override')
        self.assertIsNone(self.testvalue)

    @override_settings(TEST='override')
    def test_signal_callback_decorator(self):
        self.assertEqual(self.testvalue, 'override')

    #
    # Regression tests for #10130: deleting settings.
    #

    def test_settings_delete(self):
        settings.TEST = 'test'
        self.assertEqual('test', settings.TEST)
        del settings.TEST
        with self.assertRaises(AttributeError):
            getattr(settings, 'TEST')

    def test_settings_delete_wrapped(self):
        with self.assertRaisesMessage(TypeError, "can't delete _wrapped."):
            delattr(settings, '_wrapped')

    def test_override_settings_delete(self):
        """
        Allow deletion of a setting in an overridden settings set (#18824)
        """
        previous_i18n = settings.USE_I18N
        previous_l10n = settings.USE_L10N
        with self.settings(USE_I18N=False):
            del settings.USE_I18N
            with self.assertRaises(AttributeError):
                getattr(settings, 'USE_I18N')
            # Should also work for a non-overridden setting
            del settings.USE_L10N
            with self.assertRaises(AttributeError):
                getattr(settings, 'USE_L10N')
            self.assertNotIn('USE_I18N', dir(settings))
            self.assertNotIn('USE_L10N', dir(settings))
        self.assertEqual(settings.USE_I18N, previous_i18n)
        self.assertEqual(settings.USE_L10N, previous_l10n)

    def test_override_settings_nested(self):
        """
        override_settings uses the actual _wrapped attribute at
        runtime, not when it was instantiated.
        """

        with self.assertRaises(AttributeError):
            getattr(settings, 'TEST')
        with self.assertRaises(AttributeError):
            getattr(settings, 'TEST2')

        inner = override_settings(TEST2='override')
        with override_settings(TEST='override'):
            self.assertEqual('override', settings.TEST)
            with inner:
                self.assertEqual('override', settings.TEST)
                self.assertEqual('override', settings.TEST2)
            # inner's __exit__ should have restored the settings of the outer
            # context manager, not those when the class was instantiated
            self.assertEqual('override', settings.TEST)
            with self.assertRaises(AttributeError):
                getattr(settings, 'TEST2')

        with self.assertRaises(AttributeError):
            getattr(settings, 'TEST')
        with self.assertRaises(AttributeError):
            getattr(settings, 'TEST2')

    def test_no_secret_key(self):
        settings_module = ModuleType('fake_settings_module')
        sys.modules['fake_settings_module'] = settings_module
        msg = 'The SECRET_KEY setting must not be empty.'
        try:
            with self.assertRaisesMessage(ImproperlyConfigured, msg):
                Settings('fake_settings_module')
        finally:
            del sys.modules['fake_settings_module']

    def test_no_settings_module(self):
        msg = (
            'Requested setting%s, but settings are not configured. You '
            'must either define the environment variable DJANGO_SETTINGS_MODULE '
            'or call settings.configure() before accessing settings.'
        )
        orig_settings = os.environ[ENVIRONMENT_VARIABLE]
        os.environ[ENVIRONMENT_VARIABLE] = ''
        try:
            with self.assertRaisesMessage(ImproperlyConfigured, msg % 's'):
                settings._setup()
            with self.assertRaisesMessage(ImproperlyConfigured, msg % ' TEST'):
                settings._setup('TEST')
        finally:
            os.environ[ENVIRONMENT_VARIABLE] = orig_settings

    def test_already_configured(self):
        with self.assertRaisesMessage(RuntimeError, 'Settings already configured.'):
            settings.configure()

    @requires_tz_support
    @mock.patch('django.conf.global_settings.TIME_ZONE', 'test')
    def test_incorrect_timezone(self):
        with self.assertRaisesMessage(ValueError, 'Incorrect timezone setting: test'):
            settings._setup()


class TestComplexSettingOverride(SimpleTestCase):
    def setUp(self):
        self.old_warn_override_settings = signals.COMPLEX_OVERRIDE_SETTINGS.copy()
        signals.COMPLEX_OVERRIDE_SETTINGS.add('TEST_WARN')

    def tearDown(self):
        signals.COMPLEX_OVERRIDE_SETTINGS = self.old_warn_override_settings
        self.assertNotIn('TEST_WARN', signals.COMPLEX_OVERRIDE_SETTINGS)

    def test_complex_override_warning(self):
        """Regression test for #19031"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            with override_settings(TEST_WARN='override'):
                self.assertEqual(settings.TEST_WARN, 'override')

            self.assertEqual(len(w), 1)
            self.assertEqual(w[0].filename, __file__)
            self.assertEqual(str(w[0].message), 'Overriding setting TEST_WARN can lead to unexpected behavior.')


class SecureProxySslHeaderTest(SimpleTestCase):

    @override_settings(SECURE_PROXY_SSL_HEADER=None)
    def test_none(self):
        req = HttpRequest()
        self.assertIs(req.is_secure(), False)

    @override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTOCOL', 'https'))
    def test_set_without_xheader(self):
        req = HttpRequest()
        self.assertIs(req.is_secure(), False)

    @override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTOCOL', 'https'))
    def test_set_with_xheader_wrong(self):
        req = HttpRequest()
        req.META['HTTP_X_FORWARDED_PROTOCOL'] = 'wrongvalue'
        self.assertIs(req.is_secure(), False)

    @override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTOCOL', 'https'))
    def test_set_with_xheader_right(self):
        req = HttpRequest()
        req.META['HTTP_X_FORWARDED_PROTOCOL'] = 'https'
        self.assertIs(req.is_secure(), True)


class IsOverriddenTest(SimpleTestCase):
    def test_configure(self):
        s = LazySettings()
        s.configure(SECRET_KEY='foo')

        self.assertTrue(s.is_overridden('SECRET_KEY'))

    def test_module(self):
        settings_module = ModuleType('fake_settings_module')
        settings_module.SECRET_KEY = 'foo'
        sys.modules['fake_settings_module'] = settings_module
        try:
            s = Settings('fake_settings_module')

            self.assertTrue(s.is_overridden('SECRET_KEY'))
            self.assertFalse(s.is_overridden('ALLOWED_HOSTS'))
        finally:
            del sys.modules['fake_settings_module']

    def test_override(self):
        self.assertFalse(settings.is_overridden('ALLOWED_HOSTS'))
        with override_settings(ALLOWED_HOSTS=[]):
            self.assertTrue(settings.is_overridden('ALLOWED_HOSTS'))

    def test_unevaluated_lazysettings_repr(self):
        lazy_settings = LazySettings()
        expected = '<LazySettings [Unevaluated]>'
        self.assertEqual(repr(lazy_settings), expected)

    def test_evaluated_lazysettings_repr(self):
        lazy_settings = LazySettings()
        module = os.environ.get(ENVIRONMENT_VARIABLE)
        expected = '<LazySettings "%s">' % module
        # Force evaluation of the lazy object.
        lazy_settings.APPEND_SLASH
        self.assertEqual(repr(lazy_settings), expected)

    def test_usersettingsholder_repr(self):
        lazy_settings = LazySettings()
        lazy_settings.configure(APPEND_SLASH=False)
        expected = '<UserSettingsHolder>'
        self.assertEqual(repr(lazy_settings._wrapped), expected)

    def test_settings_repr(self):
        module = os.environ.get(ENVIRONMENT_VARIABLE)
        lazy_settings = Settings(module)
        expected = '<Settings "%s">' % module
        self.assertEqual(repr(lazy_settings), expected)


class TestListSettings(unittest.TestCase):
    """
    Make sure settings that should be lists or tuples throw
    ImproperlyConfigured if they are set to a string instead of a list or tuple.
    """
    list_or_tuple_settings = (
        "INSTALLED_APPS",
        "TEMPLATE_DIRS",
        "LOCALE_PATHS",
    )

    def test_tuple_settings(self):
        settings_module = ModuleType('fake_settings_module')
        settings_module.SECRET_KEY = 'foo'
        for setting in self.list_or_tuple_settings:
            setattr(settings_module, setting, ('non_list_or_tuple_value'))
            sys.modules['fake_settings_module'] = settings_module
            try:
                with self.assertRaises(ImproperlyConfigured):
                    Settings('fake_settings_module')
            finally:
                del sys.modules['fake_settings_module']
                delattr(settings_module, setting)
