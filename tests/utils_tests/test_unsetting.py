import unittest
from django.test.utils import override_settings
from django.utils.unsetting import uses_settings


class UnsettingTests(unittest.TestCase):

    def test_uses_settings_decorator(self):
        with override_settings(USE_TZ=True):
            @uses_settings('USE_TZ', 'use_tz')
            def foo(use_tz=None):
                return use_tz
            self.assertTrue(foo())
            self.assertEqual(foo(use_tz=None), None)
            self.assertEqual(foo(None), None)
            self.assertEqual(foo(1), 1)
            self.assertEqual(foo(use_tz=2), 2)

    def test_uses_settings_fallback(self):
        with override_settings(SOME_SETTING="whoa"):
            @uses_settings('SOME_SETTING', 'some_setting',
                           fallback_trigger_value=None)
            def foo(some_setting=None):
                return some_setting
            # The obvious case
            self.assertEqual(foo(), 'whoa')

            # Explicitly passing None (which is the fallback trigger)
            self.assertEqual(foo(some_setting=None), 'whoa')
            self.assertEqual(foo(None), 'whoa')

            self.assertEqual(foo(1), 1)
            self.assertEqual(foo(some_setting=2), 2)

    def test_dict_unsetting(self):
        setting_value = "seduced by the french"
        with override_settings(SOME_SETTING="seduced by the french"):
            @uses_settings({'SOME_SETTING': 'some_setting'})
            def foo(some_setting=None):
                return some_setting

            #When we call foo, some_setting will be replaced with SOME_SETTING.
            result = foo()

            #Hence, result is not None and is instead setting_value.
            self.assertEqual(result, setting_value)

    def test_dict_multiple_unsettings(self):
        some_setting = "seduced by the french"
        other_setting = "totally orthogonal"

        settings = {'SOME_SETTING': some_setting,
                    'OTHER_SETTING': other_setting}

        with override_settings(**settings):
            @uses_settings({'SOME_SETTING': 'some_setting',
                            'OTHER_SETTING': 'other_setting'})
            def foo(some_setting=None, other_setting=None):
                return some_setting, other_setting

            #If we pass no arguments, the settings are used.
            self.assertEqual(foo(),
                             (some_setting, other_setting)
                             )
            #the setting should be overridden by passing an argument
            self.assertEqual(foo(some_setting="devotion to the pope"),
                             ("devotion to the pope", other_setting)
                             )
