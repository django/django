from django.contrib.localflavor.cz.forms import (CZPostalCodeField,
    CZRegionSelect, CZBirthNumberField, CZICNumberField)

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase


class CZLocalFlavorTests(SimpleTestCase):
    def test_CZRegionSelect(self):
        f = CZRegionSelect()
        out = u'''<select name="regions">
<option value="PR">Prague</option>
<option value="CE">Central Bohemian Region</option>
<option value="SO">South Bohemian Region</option>
<option value="PI">Pilsen Region</option>
<option value="CA">Carlsbad Region</option>
<option value="US">Usti Region</option>
<option value="LB">Liberec Region</option>
<option value="HK">Hradec Region</option>
<option value="PA">Pardubice Region</option>
<option value="VY">Vysocina Region</option>
<option value="SM">South Moravian Region</option>
<option value="OL">Olomouc Region</option>
<option value="ZL">Zlin Region</option>
<option value="MS">Moravian-Silesian Region</option>
</select>'''
        self.assertHTMLEqual(f.render('regions', 'TT'), out)

    def test_CZPostalCodeField(self):
        error_format = [u'Enter a postal code in the format XXXXX or XXX XX.']
        valid = {
            '91909': '91909',
            '917 01': '91701',
            '12345': '12345',
        }
        invalid = {
            '84545x': error_format,
            '123456': error_format,
            '1234': error_format,
            '123 4': error_format,
        }
        self.assertFieldOutput(CZPostalCodeField, valid, invalid)

    def test_CZBirthNumberField(self):
        error_format = [u'Enter a birth number in the format XXXXXX/XXXX or XXXXXXXXXX.']
        error_invalid = [u'Enter a valid birth number.']
        valid = {
            '880523/1237': '880523/1237',
            '8805231237': '8805231237',
            '880523/000': '880523/000',
            '880523000': '880523000',
            '882101/0011': '882101/0011',
        }
        invalid = {
            '123456/12': error_format,
            '123456/12345': error_format,
            '12345612': error_format,
            '12345612345': error_format,
            '880523/1239': error_invalid,
            '8805231239': error_invalid,
            '990101/0011': error_invalid,
        }
        self.assertFieldOutput(CZBirthNumberField, valid, invalid)

    def test_CZICNumberField(self):
        error_invalid = [u'Enter a valid IC number.']
        valid ={
            '12345679': '12345679',
            '12345601': '12345601',
            '12345661': '12345661',
            '12345610': '12345610',
        }
        invalid = {
            '1234567': error_invalid,
            '12345660': error_invalid,
            '12345600': error_invalid,
        }
        self.assertFieldOutput(CZICNumberField, valid, invalid)
