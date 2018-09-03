from django.core.checks.translation import check_setting_language_code
from django.test import SimpleTestCase, override_settings


class TranslationCheckTests(SimpleTestCase):

    @override_settings(LANGUAGE_CODE="eu")
    def test_valid_language_code_format_ll_only(self):
        result = check_setting_language_code(None)
        self.assertEqual(len(result), 0)

    @override_settings(LANGUAGE_CODE="eü")
    def test_invalid_language_code_format_ll_only(self):
        result = check_setting_language_code(None)
        self.assertEqual(len(result), 1)
        error = result[0]
        self.assertEqual(error.id, 'translation.E001')
        self.assertEqual(error.msg, (
            "LANGUAGE_CODE in settings.py is eü. It should be in the form ll or ll-cc where ll is the language and cc "
            "is the country. Examples include: it, de-at, es, pt-br. The full set of language codes specifications is "
            "outlined by https://en.wikipedia.org/wiki/IETF_language_tag#Syntax_of_language_tags"
        ))

    @override_settings(LANGUAGE_CODE="en-US")
    def test_valid_language_code_format_ll_cc(self):
        result = check_setting_language_code(None)
        self.assertEqual(len(result), 0)

    @override_settings(LANGUAGE_CODE="en_US")
    def test_invalid_language_code_format_ll_cc(self):
        result = check_setting_language_code(None)
        self.assertEqual(len(result), 1)
        error = result[0]
        self.assertEqual(error.id, 'translation.E001')
        self.assertEqual(error.msg, (
            "LANGUAGE_CODE in settings.py is en_US. It should be in the form ll or ll-cc where ll is the language and "
            "cc is the country. Examples include: it, de-at, es, pt-br. The full set of language codes specifications "
            "is outlined by https://en.wikipedia.org/wiki/IETF_language_tag#Syntax_of_language_tags"
        ))
