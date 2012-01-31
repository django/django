from django.contrib.localflavor.in_.forms import (INZipCodeField,
    INStateField, INStateSelect, INPhoneNumberField)

from django.test import SimpleTestCase



class INLocalFlavorTests(SimpleTestCase):
    def test_INPhoneNumberField(self):
        error_format = [u'Phone numbers must be in 02X-8X or 03X-7X or 04X-6X format.']
        valid = {
            '0423-2443667': '0423-2443667',
            '0423 2443667': '0423 2443667',
            '04236-244366': '04236-244366',
            '040-24436678': '040-24436678',
        }
        invalid = {
            '04-2443667': error_format,
            '423-2443667': error_format,
            '0423-9442667': error_format,
            '0423-0443667': error_format,
            '0423-244366': error_format,
            '04232442667': error_format,
            '0423DJANGO': error_format,
        }
        self.assertFieldOutput(INPhoneNumberField, valid, invalid)

    def test_INPStateSelect(self):
        f = INStateSelect()
        out = u'''<select name="state">
<option value="KA">Karnataka</option>
<option value="AP" selected="selected">Andhra Pradesh</option>
<option value="KL">Kerala</option>
<option value="TN">Tamil Nadu</option>
<option value="MH">Maharashtra</option>
<option value="UP">Uttar Pradesh</option>
<option value="GA">Goa</option>
<option value="GJ">Gujarat</option>
<option value="RJ">Rajasthan</option>
<option value="HP">Himachal Pradesh</option>
<option value="JK">Jammu and Kashmir</option>
<option value="AR">Arunachal Pradesh</option>
<option value="AS">Assam</option>
<option value="BR">Bihar</option>
<option value="CG">Chattisgarh</option>
<option value="HR">Haryana</option>
<option value="JH">Jharkhand</option>
<option value="MP">Madhya Pradesh</option>
<option value="MN">Manipur</option>
<option value="ML">Meghalaya</option>
<option value="MZ">Mizoram</option>
<option value="NL">Nagaland</option>
<option value="OR">Orissa</option>
<option value="PB">Punjab</option>
<option value="SK">Sikkim</option>
<option value="TR">Tripura</option>
<option value="UA">Uttarakhand</option>
<option value="WB">West Bengal</option>
<option value="AN">Andaman and Nicobar</option>
<option value="CH">Chandigarh</option>
<option value="DN">Dadra and Nagar Haveli</option>
<option value="DD">Daman and Diu</option>
<option value="DL">Delhi</option>
<option value="LD">Lakshadweep</option>
<option value="PY">Pondicherry</option>
</select>'''
        self.assertHTMLEqual(f.render('state', 'AP'), out)

    def test_INZipCodeField(self):
        error_format = [u'Enter a zip code in the format XXXXXX or XXX XXX.']
        valid = {
            '360311': '360311',
            '360 311': '360311',
        }
        invalid = {
            '36 0311': error_format,
            '3603111': error_format,
            '360 31': error_format,
            '36031': error_format,
            'O2B 2R3': error_format
        }
        self.assertFieldOutput(INZipCodeField, valid, invalid)

    def test_INStateField(self):
        error_format = [u'Enter an Indian state or territory.']
        valid = {
            'an': 'AN',
            'AN': 'AN',
            'andaman and nicobar': 'AN',
            'andra pradesh': 'AP',
            'andrapradesh': 'AP',
            'andhrapradesh': 'AP',
            'ap': 'AP',
            'andhra pradesh': 'AP',
            'ar': 'AR',
            'arunachal pradesh': 'AR',
            'assam': 'AS',
            'as': 'AS',
            'bihar': 'BR',
            'br': 'BR',
            'cg': 'CG',
            'chattisgarh': 'CG',
            'ch': 'CH',
            'chandigarh': 'CH',
            'daman and diu': 'DD',
            'dd': 'DD',
            'dl': 'DL',
            'delhi': 'DL',
            'dn': 'DN',
            'dadra and nagar haveli': 'DN',
            'ga': 'GA',
            'goa': 'GA',
            'gj': 'GJ',
            'gujarat': 'GJ',
            'himachal pradesh': 'HP',
            'hp': 'HP',
            'hr': 'HR',
            'haryana': 'HR',
            'jharkhand': 'JH',
            'jh': 'JH',
            'jammu and kashmir': 'JK',
            'jk': 'JK',
            'karnataka': 'KA',
            'karnatka': 'KA',
            'ka': 'KA',
            'kerala': 'KL',
            'kl': 'KL',
            'ld': 'LD',
            'lakshadweep': 'LD',
            'maharastra': 'MH',
            'mh': 'MH',
            'maharashtra': 'MH',
            'meghalaya': 'ML',
            'ml': 'ML',
            'mn': 'MN',
            'manipur': 'MN',
            'madhya pradesh': 'MP',
            'mp': 'MP',
            'mizoram': 'MZ',
            'mizo': 'MZ',
            'mz': 'MZ',
            'nl': 'NL',
            'nagaland': 'NL',
            'orissa': 'OR',
            'odisa': 'OR',
            'orisa': 'OR',
            'or': 'OR',
            'pb': 'PB',
            'punjab': 'PB',
            'py': 'PY',
            'pondicherry': 'PY',
            'rajasthan': 'RJ',
            'rajastan': 'RJ',
            'rj': 'RJ',
            'sikkim': 'SK',
            'sk': 'SK',
            'tamil nadu': 'TN',
            'tn': 'TN',
            'tamilnadu': 'TN',
            'tamilnad': 'TN',
            'tr': 'TR',
            'tripura': 'TR',
            'ua': 'UA',
            'uttarakhand': 'UA',
            'up': 'UP',
            'uttar pradesh': 'UP',
            'westbengal': 'WB',
            'bengal': 'WB',
            'wb': 'WB',
            'west bengal': 'WB'
        }
        invalid = {
            'florida': error_format,
            'FL': error_format,
        }
        self.assertFieldOutput(INStateField, valid, invalid)
