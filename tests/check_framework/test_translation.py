from django.core.checks.translation import E001, check_setting_language_code
from django.test import SimpleTestCase, override_settings


class TranslationCheckTests(SimpleTestCase):

    def test_valid_language_code(self):
        tags = (
            'en',              # language
            'mas',             # language
            'sgn-ase',         # language+extlang
            'fr-CA',           # language+region
            'es-419',          # language+region
            'zh-Hans',         # language+script
            'ca-ES-valencia',  # language+region+variant
            # FIXME: The following should be invalid:
            'sr@latin',        # language+script
        )
        for tag in tags:
            with self.subTest(tag), override_settings(LANGUAGE_CODE=tag):
                self.assertEqual(check_setting_language_code(None), [])

    def test_invalid_language_code(self):
        tags = (
            'eü',              # non-latin characters.
            'en_US',           # locale format.
            'en--us',          # empty subtag.
            '-en',             # leading separator.
            'en-',             # trailing separator.
            'en-US.UTF-8',     # language tag w/ locale encoding.
            'en_US.UTF-8',     # locale format - languate w/ region and encoding.
            'ca_ES@valencia',  # locale format - language w/ region and variant.
            # FIXME: The following should be invalid:
            # 'sr@latin',      # locale instead of language tag.
        )
        for tag in tags:
            with self.subTest(tag), override_settings(LANGUAGE_CODE=tag):
                result = check_setting_language_code(None)
                self.assertEqual(result, [E001])
                self.assertEqual(result[0].id, 'translation.E001')
                self.assertEqual(result[0].msg, 'You have provided an invalid value for the LANGUAGE_CODE setting.')
