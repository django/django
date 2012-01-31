from django.contrib.localflavor.nl.forms import (NLPhoneNumberField,
    NLZipCodeField, NLSoFiNumberField, NLProvinceSelect)

from django.test import SimpleTestCase


class NLLocalFlavorTests(SimpleTestCase):
    def test_NLProvinceSelect(self):
        f = NLProvinceSelect()
        out = u'''<select name="provinces">
<option value="DR">Drenthe</option>
<option value="FL">Flevoland</option>
<option value="FR">Friesland</option>
<option value="GL">Gelderland</option>
<option value="GR">Groningen</option>
<option value="LB">Limburg</option>
<option value="NB">Noord-Brabant</option>
<option value="NH">Noord-Holland</option>
<option value="OV" selected="selected">Overijssel</option>
<option value="UT">Utrecht</option>
<option value="ZE">Zeeland</option>
<option value="ZH">Zuid-Holland</option>
</select>'''
        self.assertHTMLEqual(f.render('provinces', 'OV'), out)

    def test_NLPhoneNumberField(self):
        error_invalid = [u'Enter a valid phone number']
        valid = {
                '012-3456789': '012-3456789',
                '0123456789': '0123456789',
                '+31-12-3456789': '+31-12-3456789',
                '(0123) 456789': '(0123) 456789',
        }
        invalid = {
                'foo': error_invalid,
        }
        self.assertFieldOutput(NLPhoneNumberField, valid, invalid)

    def test_NLZipCodeField(self):
        error_invalid = [u'Enter a valid postal code']
        valid = {
            '1234ab': '1234 AB',
            '1234 ab': '1234 AB',
            '1234 AB': '1234 AB',
        }
        invalid = {
            '0123AB': error_invalid,
            'foo': error_invalid,
        }
        self.assertFieldOutput(NLZipCodeField, valid, invalid)

    def test_NLSoFiNumberField(self):
        error_invalid = [u'Enter a valid SoFi number']
        valid = {
            '123456782': '123456782',
        }
        invalid = {
            '000000000': error_invalid,
            '123456789': error_invalid,
            'foo': error_invalid,
        }
        self.assertFieldOutput(NLSoFiNumberField, valid, invalid)
