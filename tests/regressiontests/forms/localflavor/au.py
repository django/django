from django.contrib.localflavor.au.forms import (AUPostCodeField,
        AUPhoneNumberField, AUStateSelect)

from utils import LocalFlavorTestCase


class AULocalFlavorTests(LocalFlavorTestCase):
    def test_AUStateSelect(self):
        f = AUStateSelect()
        out = u'''<select name="state">
<option value="ACT">Australian Capital Territory</option>
<option value="NSW" selected="selected">New South Wales</option>
<option value="NT">Northern Territory</option>
<option value="QLD">Queensland</option>
<option value="SA">South Australia</option>
<option value="TAS">Tasmania</option>
<option value="VIC">Victoria</option>
<option value="WA">Western Australia</option>
</select>'''
        self.assertEqual(f.render('state', 'NSW'), out)

    def test_AUPostCodeField(self):
        error_format = [u'Enter a 4 digit post code.']
        valid = {
            '1234': '1234',
            '2000': '2000',
        }
        invalid = {
            'abcd': error_format,
            '20001': error_format,
        }
        self.assertFieldOutput(AUPostCodeField, valid, invalid)

    def test_AUPhoneNumberField(self):
        error_format = [u'Phone numbers must contain 10 digits.']
        valid = {
            '1234567890': '1234567890',
            '0213456789': '0213456789',
            '02 13 45 67 89': '0213456789',
            '(02) 1345 6789': '0213456789',
            '(02) 1345-6789': '0213456789',
            '(02)1345-6789': '0213456789',
            '0408 123 456': '0408123456',
        }
        invalid = {
            '123': error_format,
            '1800DJANGO': error_format,
        }
        self.assertFieldOutput(AUPhoneNumberField, valid, invalid)

