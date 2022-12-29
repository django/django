from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from django.utils.translation import activate, get_language

here = Path(__file__).parent.parent
tests_dir = here.parent.parent
extended_locale_paths = settings.LOCALE_PATHS + [
    tests_dir / "i18n" / "other" / "locale",
]


class MultipleLocaleActivationTestCase(SimpleTestCase):
    """
    Tests for template rendering when multiple locales are activated during the
    lifetime of the same process.
    """

    def setUp(self):
        self._old_language = get_language()

    def tearDown(self):
        activate(self._old_language)
