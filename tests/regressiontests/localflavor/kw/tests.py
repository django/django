from django.contrib.localflavor.kw.forms import KWCivilIDNumberField

from django.test import SimpleTestCase


class KWLocalFlavorTests(SimpleTestCase):
    def test_KWCivilIDNumberField(self):
        error_invalid = [u'Enter a valid Kuwaiti Civil ID number']
        valid = {
            '282040701483': '282040701483',
        }
        invalid = {
            '289332013455': error_invalid,
        }
        self.assertFieldOutput(KWCivilIDNumberField, valid, invalid)
