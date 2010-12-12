from django.contrib.localflavor.at.forms import (ATZipCodeField, ATStateSelect,
    ATSocialSecurityNumberField)

from utils import LocalFlavorTestCase


class ATLocalFlavorTests(LocalFlavorTestCase):
    def test_ATStateSelect(self):
        f = ATStateSelect()
        out = u'''<select name="bundesland">
<option value="BL">Burgenland</option>
<option value="KA">Carinthia</option>
<option value="NO">Lower Austria</option>
<option value="OO">Upper Austria</option>
<option value="SA">Salzburg</option>
<option value="ST">Styria</option>
<option value="TI">Tyrol</option>
<option value="VO">Vorarlberg</option>
<option value="WI" selected="selected">Vienna</option>
</select>'''
        self.assertEqual(f.render('bundesland', 'WI'), out)

    def test_ATZipCodeField(self):
        error_format = [u'Enter a zip code in the format XXXX.']
        valid = {
            '1150': '1150',
            '4020': '4020',
            '8020': '8020',
        }
        invalid = {
            '111222': error_format,
            'eeffee': error_format,
        }
        self.assertFieldOutput(ATZipCodeField, valid, invalid)

    def test_ATSocialSecurityNumberField(self):
        error_format = [u'Enter a valid Austrian Social Security Number in XXXX XXXXXX format.']
        valid = {
            '1237 010180': '1237 010180',
        }
        invalid = {
            '1237 010181': error_format,
            '12370 010180': error_format,
        }
        self.assertFieldOutput(ATSocialSecurityNumberField, valid, invalid)
