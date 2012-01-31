from django.contrib.localflavor.ch.forms import (CHZipCodeField,
    CHPhoneNumberField, CHIdentityCardNumberField, CHStateSelect)

from django.test import SimpleTestCase


class CHLocalFlavorTests(SimpleTestCase):
    def test_CHStateSelect(self):
        f = CHStateSelect()
        out = u'''<select name="state">
<option value="AG" selected="selected">Aargau</option>
<option value="AI">Appenzell Innerrhoden</option>
<option value="AR">Appenzell Ausserrhoden</option>
<option value="BS">Basel-Stadt</option>
<option value="BL">Basel-Land</option>
<option value="BE">Berne</option>
<option value="FR">Fribourg</option>
<option value="GE">Geneva</option>
<option value="GL">Glarus</option>
<option value="GR">Graubuenden</option>
<option value="JU">Jura</option>
<option value="LU">Lucerne</option>
<option value="NE">Neuchatel</option>
<option value="NW">Nidwalden</option>
<option value="OW">Obwalden</option>
<option value="SH">Schaffhausen</option>
<option value="SZ">Schwyz</option>
<option value="SO">Solothurn</option>
<option value="SG">St. Gallen</option>
<option value="TG">Thurgau</option>
<option value="TI">Ticino</option>
<option value="UR">Uri</option>
<option value="VS">Valais</option>
<option value="VD">Vaud</option>
<option value="ZG">Zug</option>
<option value="ZH">Zurich</option>
</select>'''
        self.assertHTMLEqual(f.render('state', 'AG'), out)

    def test_CHZipCodeField(self):
        error_format = [u'Enter a zip code in the format XXXX.']
        valid = {
            '1234': '1234',
            '0000': '0000',
        }
        invalid = {
            '800x': error_format,
            '80 00': error_format,
        }
        self.assertFieldOutput(CHZipCodeField, valid, invalid)

    def test_CHPhoneNumberField(self):
        error_format = [u'Phone numbers must be in 0XX XXX XX XX format.']
        valid = {
            '012 345 67 89': '012 345 67 89',
            '0123456789': '012 345 67 89',
        }
        invalid = {
            '01234567890': error_format,
            '1234567890': error_format,
        }
        self.assertFieldOutput(CHPhoneNumberField, valid, invalid)

    def test_CHIdentityCardNumberField(self):
        error_format = [u'Enter a valid Swiss identity or passport card number in X1234567<0 or 1234567890 format.']
        valid = {
            'C1234567<0': 'C1234567<0',
            '2123456700': '2123456700',
        }
        invalid = {
            'C1234567<1': error_format,
            '2123456701': error_format,
        }
        self.assertFieldOutput(CHIdentityCardNumberField, valid, invalid)
