from django.contrib.localflavor.ca.forms import (CAPostalCodeField,
        CAPhoneNumberField, CAProvinceField, CAProvinceSelect,
        CASocialInsuranceNumberField)

from utils import LocalFlavorTestCase


class CALocalFlavorTests(LocalFlavorTestCase):
    def test_CAProvinceSelect(self):
        f = CAProvinceSelect()
        out = u'''<select name="province">
<option value="AB" selected="selected">Alberta</option>
<option value="BC">British Columbia</option>
<option value="MB">Manitoba</option>
<option value="NB">New Brunswick</option>
<option value="NF">Newfoundland and Labrador</option>
<option value="NT">Northwest Territories</option>
<option value="NS">Nova Scotia</option>
<option value="NU">Nunavut</option>
<option value="ON">Ontario</option>
<option value="PE">Prince Edward Island</option>
<option value="QC">Quebec</option>
<option value="SK">Saskatchewan</option>
<option value="YK">Yukon</option>
</select>'''
        self.assertEqual(f.render('province', 'AB'), out)

    def test_CAPostalCodeField(self):
        error_format = [u'Enter a postal code in the format XXX XXX.']
        valid = {
            'T2S 2H7': 'T2S 2H7',
            'T2S 2W7': 'T2S 2W7',
            'T2S 2Z7': 'T2S 2Z7',
            'T2Z 2H7': 'T2Z 2H7',

        }
        invalid = {
            'T2S2H7' : error_format,
            'T2S 2H' : error_format,
            '2T6 H8I': error_format,
            'T2S2H' : error_format,
            90210 : error_format,
            'W2S 2H3': error_format,
            'Z2S 2H3': error_format,
            'F2S 2H3': error_format,
            'A2S 2D3': error_format,
            'A2I 2R3': error_format,
            'A2Q 2R3': error_format,
            'U2B 2R3': error_format,
            'O2B 2R3': error_format,
        }
        self.assertFieldOutput(CAPostalCodeField, valid, invalid)

    def test_CAPhoneNumberField(self):
        error_format = [u'Phone numbers must be in XXX-XXX-XXXX format.']
        valid = {
            '403-555-1212': '403-555-1212',
            '4035551212': '403-555-1212',
            '403 555-1212': '403-555-1212',
            '(403) 555-1212': '403-555-1212',
            '403 555 1212': '403-555-1212',
            '403.555.1212': '403-555-1212',
            '403.555-1212': '403-555-1212',
            ' (403) 555.1212 ': '403-555-1212',
        }
        invalid = {
           '555-1212': error_format,
           '403-55-1212': error_format,
        }
        self.assertFieldOutput(CAPhoneNumberField, valid, invalid)

    def test_CAProvinceField(self):
        error_format = [u'Enter a Canadian province or territory.']
        valid = {
            'ab': 'AB',
            'BC': 'BC',
            'nova scotia': 'NS',
            '  manitoba ': 'MB',
        }
        invalid = {
            'T2S 2H7': error_format,
        }
        self.assertFieldOutput(CAProvinceField, valid, invalid)

    def test_CASocialInsuranceField(self):
        error_format = [u'Enter a valid Canadian Social Insurance number in XXX-XXX-XXX format.']
        valid = {
            '046-454-286': '046-454-286',
        }
        invalid = {
            '046-454-287': error_format,
            '046 454 286': error_format,
            '046-44-286': error_format,
        }
        self.assertFieldOutput(CASocialInsuranceNumberField, valid, invalid)
