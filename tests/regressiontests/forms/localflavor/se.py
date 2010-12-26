# -*- coding: utf-8 -*-
from django.contrib.localflavor.se.forms import (SECountySelect,
    SEOrganisationNumberField, SEPersonalIdentityNumberField,
    SEPostalCodeField)
import datetime

from utils import LocalFlavorTestCase


class SELocalFlavorTests(LocalFlavorTestCase):

    def setUp(self):
        # Mocking datetime.date to make sure
        # localflavor.se.utils.validate_id_birthday works
        class MockDate(datetime.date):
            def today(cls):
                return datetime.date(2008, 5, 14)
            today = classmethod(today)
        self._olddate = datetime.date
        datetime.date = MockDate

    def tearDown(self):
        datetime.date = self._olddate

    def test_SECountySelect(self):
        f = SECountySelect()
        out = u'''<select name="swedish_county">
<option value="AB">Stockholm</option>
<option value="AC">V\xe4sterbotten</option>
<option value="BD">Norrbotten</option>
<option value="C">Uppsala</option>
<option value="D">S\xf6dermanland</option>
<option value="E" selected="selected">\xd6sterg\xf6tland</option>
<option value="F">J\xf6nk\xf6ping</option>
<option value="G">Kronoberg</option>
<option value="H">Kalmar</option>
<option value="I">Gotland</option>
<option value="K">Blekinge</option>
<option value="M">Sk\xe5ne</option>
<option value="N">Halland</option>
<option value="O">V\xe4stra G\xf6taland</option>
<option value="S">V\xe4rmland</option>
<option value="T">\xd6rebro</option>
<option value="U">V\xe4stmanland</option>
<option value="W">Dalarna</option>
<option value="X">G\xe4vleborg</option>
<option value="Y">V\xe4sternorrland</option>
<option value="Z">J\xe4mtland</option>
</select>'''
        self.assertEqual(f.render('swedish_county', 'E'), out)

    def test_SEOrganizationNumberField(self):
        error_invalid = [u'Enter a valid Swedish organisation number.']
        valid = {
            '870512-1989': '198705121989',
            '19870512-1989': '198705121989',
            '870512-2128': '198705122128',
            '081015-6315': '190810156315',
            '081015+6315': '180810156315',
            '0810156315': '190810156315',
            # Test some different organisation numbers
            # IKEA Linköping
            '556074-7569': '5560747569',
            # Volvo Personvagnar
            '556074-3089': '5560743089',
            # LJS (organisation)
            '822001-5476': '8220015476',
            # LJS (organisation)
            '8220015476': '8220015476',
            # Katedralskolan Linköping (school)
            '2120000449': '2120000449',
            # Faux organisation number, which tests that the checksum can be 0
            '232518-5060': '2325185060',
        }
        invalid = {
            # Ordinary personal identity numbers for sole proprietors
            # The same rules as for SEPersonalIdentityField applies here
            '081015 6315': error_invalid,
            '950231-4496': error_invalid,
            '6914104499': error_invalid,
            '950d314496': error_invalid,
            'invalid!!!': error_invalid,
            '870514-1111': error_invalid,
            # Co-ordination number checking
            # Co-ordination numbers are not valid organisation numbers
            '870574-1315': error_invalid,
            '870573-1311': error_invalid,
            # Volvo Personvagnar, bad format
            '556074+3089': error_invalid,
            # Invalid checksum
            '2120000441': error_invalid,
            # Valid checksum but invalid organisation type
            '1120000441': error_invalid,
        }
        self.assertFieldOutput(SEOrganisationNumberField, valid, invalid)

    def test_SEPersonalIdentityNumberField(self):
        error_invalid = [u'Enter a valid Swedish personal identity number.']
        error_coord = [u'Co-ordination numbers are not allowed.']
        valid = {
            '870512-1989': '198705121989',
            '870512-2128': '198705122128',
            '19870512-1989': '198705121989',
            '198705121989': '198705121989',
            '081015-6315': '190810156315',
            '0810156315': '190810156315',
            # This is a "special-case" in the checksum calculation,
            # where the sum is divisible by 10 (the checksum digit == 0)
            '8705141060': '198705141060',
            # + means that the person is older than 100 years
            '081015+6315': '180810156315',
            # Co-ordination number checking
            '870574-1315': '198705741315',
            '870574+1315': '188705741315',
            '198705741315': '198705741315',
        }
        invalid = {
            '081015 6315': error_invalid,
            '950d314496': error_invalid,
            'invalid!!!': error_invalid,
            # Invalid dates
            # February 31st does not exist
            '950231-4496': error_invalid,
            # Month 14 does not exist
            '6914104499': error_invalid,
            # There are no Swedish personal id numbers where year < 1800
            '17430309-7135': error_invalid,
            # Invalid checksum
            '870514-1111': error_invalid,
            # Co-ordination number with bad checksum
            '870573-1311': error_invalid,
        }
        self.assertFieldOutput(SEPersonalIdentityNumberField, valid, invalid)

        valid = {}
        invalid = {
            # Check valid co-ordination numbers that should not be accepted
            # because of coordination_number=False
            '870574-1315': error_coord,
            '870574+1315': error_coord,
            '8705741315': error_coord,
            # Invalid co-ordination numbers should be treated as invalid, and not
            # as co-ordination numbers
            '870573-1311': error_invalid,
        }
        kwargs = {'coordination_number': False,}
        self.assertFieldOutput(SEPersonalIdentityNumberField, valid, invalid,
            field_kwargs=kwargs)

    def test_SEPostalCodeField(self):
        error_format = [u'Enter a Swedish postal code in the format XXXXX.']
        valid = {
            '589 37': '58937',
            '58937': '58937',
        }
        invalid = {
            'abcasfassadf': error_format,
            # Only one space is allowed for separation
            '589  37': error_format,
            # The postal code must not start with 0
            '01234': error_format,

        }
        self.assertFieldOutput(SEPostalCodeField, valid, invalid)

