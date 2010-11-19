from django.contrib.localflavor.de.forms import (DEZipCodeField, DEStateSelect,
    DEIdentityCardNumberField)

from utils import LocalFlavorTestCase


class DELocalFlavorTests(LocalFlavorTestCase):
    def test_DEStateSelect(self):
        f = DEStateSelect()
        out = u'''<select name="states">
<option value="BW">Baden-Wuerttemberg</option>
<option value="BY">Bavaria</option>
<option value="BE">Berlin</option>
<option value="BB">Brandenburg</option>
<option value="HB">Bremen</option>
<option value="HH">Hamburg</option>
<option value="HE">Hessen</option>
<option value="MV">Mecklenburg-Western Pomerania</option>
<option value="NI">Lower Saxony</option>
<option value="NW">North Rhine-Westphalia</option>
<option value="RP">Rhineland-Palatinate</option>
<option value="SL">Saarland</option>
<option value="SN">Saxony</option>
<option value="ST">Saxony-Anhalt</option>
<option value="SH">Schleswig-Holstein</option>
<option value="TH" selected="selected">Thuringia</option>
</select>'''
        self.assertEqual(f.render('states', 'TH'), out)

    def test_DEZipCodeField(self):
        error_format = [u'Enter a zip code in the format XXXXX.']
        valid = {
            '99423': '99423',
        }
        invalid = {
            ' 99423': error_format,
        }
        self.assertFieldOutput(DEZipCodeField, valid, invalid)

    def test_DEIdentityCardNumberField(self):
        error_format = [u'Enter a valid German identity card number in XXXXXXXXXXX-XXXXXXX-XXXXXXX-X format.']
        valid = {
            '7549313035D-6004103-0903042-0': '7549313035D-6004103-0903042-0',
            '9786324830D 6104243 0910271 2': '9786324830D-6104243-0910271-2',
        }
        invalid = {
            '0434657485D-6407276-0508137-9': error_format,
        }
        self.assertFieldOutput(DEIdentityCardNumberField, valid, invalid)
