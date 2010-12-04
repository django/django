from django.test import TestCase
from django.forms import *

from django.contrib.localflavor.be.forms import (BEPostalCodeField,
    BEPhoneNumberField, BERegionSelect, BEProvinceSelect)

class BELocalFlavorTests(TestCase):
    """
    Test case to validate BE localflavor
    """
    def assertRaisesErrorWithMessage(self, error, message, callable, *args, **kwargs):
        self.assertRaises(error, callable, *args, **kwargs)
        try:
            callable(*args, **kwargs)
        except error, e:
            self.assertEqual(message, str(e))

    def test_postal_code_field(self):
        f = BEPostalCodeField()
        self.assertEqual(u'1451', f.clean('1451'))
        self.assertEqual(u'2540', f.clean('2540'))
        err_message = "[u'Enter a valid postal code in the range and format 1XXX - 9XXX.']"
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '0287')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '14309')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '873')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '35 74')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '859A')
        err_message = "[u'This field is required.']"
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '')
        f = BEPostalCodeField(required=False)
        self.assertEqual(u'1451', f.clean('1451'))
        self.assertEqual(u'2540', f.clean('2540'))
        self.assertEqual(u'', f.clean(''))
        err_message = "[u'Enter a valid postal code in the range and format 1XXX - 9XXX.']"
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '0287')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '14309')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '873')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '35 74')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '859A')

    def test_phone_number_field(self):
        f = BEPhoneNumberField()
        self.assertEqual(u'01 234 56 78', f.clean('01 234 56 78'))
        self.assertEqual(u'01/234.56.78', f.clean('01/234.56.78'))
        self.assertEqual(u'01.234.56.78', f.clean('01.234.56.78'))
        self.assertEqual(u'012 34 56 78', f.clean('012 34 56 78'))
        self.assertEqual(u'012/34.56.78', f.clean('012/34.56.78'))
        self.assertEqual(u'012.34.56.78', f.clean('012.34.56.78'))
        self.assertEqual(u'0412 34 56 78', f.clean('0412 34 56 78'))
        self.assertEqual(u'0412/34.56.78', f.clean('0412/34.56.78'))
        self.assertEqual(u'0412.34.56.78', f.clean('0412.34.56.78'))
        self.assertEqual(u'012345678', f.clean('012345678'))
        self.assertEqual(u'0412345678', f.clean('0412345678'))
        err_message = "[u'Enter a valid phone number in one of the formats 0x xxx xx xx, 0xx xx xx xx, 04xx xx xx xx, 0x/xxx.xx.xx, 0xx/xx.xx.xx, 04xx/xx.xx.xx, 0x.xxx.xx.xx, 0xx.xx.xx.xx, 04xx.xx.xx.xx, 0xxxxxxxx or 04xxxxxxxx.']"
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '01234567')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '12/345.67.89')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '012/345.678.90')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '012/34.56.789')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '0123/45.67.89')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '012/345 678 90')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '012/34 56 789')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '012.34 56 789')
        err_message = "[u'This field is required.']"
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '')
        f = BEPhoneNumberField(required=False)
        self.assertEqual(u'01 234 56 78', f.clean('01 234 56 78'))
        self.assertEqual(u'01/234.56.78', f.clean('01/234.56.78'))
        self.assertEqual(u'01.234.56.78', f.clean('01.234.56.78'))
        self.assertEqual(u'012 34 56 78', f.clean('012 34 56 78'))
        self.assertEqual(u'012/34.56.78', f.clean('012/34.56.78'))
        self.assertEqual(u'012.34.56.78', f.clean('012.34.56.78'))
        self.assertEqual(u'0412 34 56 78', f.clean('0412 34 56 78'))
        self.assertEqual(u'0412/34.56.78', f.clean('0412/34.56.78'))
        self.assertEqual(u'0412.34.56.78', f.clean('0412.34.56.78'))
        self.assertEqual(u'012345678', f.clean('012345678'))
        self.assertEqual(u'0412345678', f.clean('0412345678'))
        self.assertEqual(u'', f.clean(''))
        err_message = "[u'Enter a valid phone number in one of the formats 0x xxx xx xx, 0xx xx xx xx, 04xx xx xx xx, 0x/xxx.xx.xx, 0xx/xx.xx.xx, 04xx/xx.xx.xx, 0x.xxx.xx.xx, 0xx.xx.xx.xx, 04xx.xx.xx.xx, 0xxxxxxxx or 04xxxxxxxx.']"
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '01234567')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '12/345.67.89')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '012/345.678.90')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '012/34.56.789')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '0123/45.67.89')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '012/345 678 90')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '012/34 56 789')
        self.assertRaisesErrorWithMessage(ValidationError, err_message, f.clean, '012.34 56 789')

    def test_region_field(self):
        w = BERegionSelect()
        self.assertEqual(u'<select name="regions">\n<option value="BRU">Brussels Capital Region</option>\n<option value="VLG" selected="selected">Flemish Region</option>\n<option value="WAL">Wallonia</option>\n</select>', w.render('regions', 'VLG'))

    def test_province_field(self):
        w = BEProvinceSelect()
        self.assertEqual(u'<select name="provinces">\n<option value="VAN">Antwerp</option>\n<option value="BRU">Brussels</option>\n<option value="VOV">East Flanders</option>\n<option value="VBR">Flemish Brabant</option>\n<option value="WHT">Hainaut</option>\n<option value="WLG" selected="selected">Liege</option>\n<option value="VLI">Limburg</option>\n<option value="WLX">Luxembourg</option>\n<option value="WNA">Namur</option>\n<option value="WBR">Walloon Brabant</option>\n<option value="VWV">West Flanders</option>\n</select>', w.render('provinces', 'WLG'))
