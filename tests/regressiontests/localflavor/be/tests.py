from django.contrib.localflavor.be.forms import (BEPostalCodeField,
    BEPhoneNumberField, BERegionSelect, BEProvinceSelect)

from django.test import SimpleTestCase


class BELocalFlavorTests(SimpleTestCase):
    def test_BEPostalCodeField(self):
        error_format = [u'Enter a valid postal code in the range and format 1XXX - 9XXX.']
        valid = {
            u'1451': '1451',
            u'2540': '2540',
        }
        invalid = {
            '0287': error_format,
            '14309': error_format,
            '873': error_format,
            '35 74': error_format,
            '859A': error_format,
        }
        self.assertFieldOutput(BEPostalCodeField, valid, invalid)

    def test_BEPhoneNumberField(self):
        error_format = [
            ('Enter a valid phone number in one of the formats 0x xxx xx xx, '
                '0xx xx xx xx, 04xx xx xx xx, 0x/xxx.xx.xx, 0xx/xx.xx.xx, '
                '04xx/xx.xx.xx, 0x.xxx.xx.xx, 0xx.xx.xx.xx, 04xx.xx.xx.xx, '
                '0xxxxxxxx or 04xxxxxxxx.')
        ]
        valid = {
            u'01 234 56 78': '01 234 56 78',
            u'01/234.56.78': '01/234.56.78',
            u'01.234.56.78': '01.234.56.78',
            u'012 34 56 78': '012 34 56 78',
            u'012/34.56.78': '012/34.56.78',
            u'012.34.56.78': '012.34.56.78',
            u'0412 34 56 78': '0412 34 56 78',
            u'0412/34.56.78': '0412/34.56.78',
            u'0412.34.56.78': '0412.34.56.78',
            u'012345678': '012345678',
            u'0412345678': '0412345678',
        }
        invalid = {
            '01234567': error_format,
            '12/345.67.89': error_format,
            '012/345.678.90': error_format,
            '012/34.56.789': error_format,
            '0123/45.67.89': error_format,
            '012/345 678 90': error_format,
            '012/34 56 789': error_format,
            '012.34 56 789': error_format,
        }
        self.assertFieldOutput(BEPhoneNumberField, valid, invalid)

    def test_BERegionSelect(self):
        f = BERegionSelect()
        out = u'''<select name="regions">
<option value="BRU">Brussels Capital Region</option>
<option value="VLG" selected="selected">Flemish Region</option>
<option value="WAL">Wallonia</option>
</select>'''
        self.assertHTMLEqual(f.render('regions', 'VLG'), out)

    def test_BEProvinceSelect(self):
        f = BEProvinceSelect()
        out = u'''<select name="provinces">
<option value="VAN">Antwerp</option>
<option value="BRU">Brussels</option>
<option value="VOV">East Flanders</option>
<option value="VBR">Flemish Brabant</option>
<option value="WHT">Hainaut</option>
<option value="WLG" selected="selected">Liege</option>
<option value="VLI">Limburg</option>
<option value="WLX">Luxembourg</option>
<option value="WNA">Namur</option>
<option value="WBR">Walloon Brabant</option>
<option value="VWV">West Flanders</option>
</select>'''
        self.assertHTMLEqual(f.render('provinces', 'WLG'), out)
