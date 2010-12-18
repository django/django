# -*- coding: utf-8 -*-
from django.contrib.localflavor.ro.forms import (ROCIFField, ROCNPField,
    ROCountyField, ROCountySelect, ROIBANField, ROPhoneNumberField,
    ROPostalCodeField)

from utils import LocalFlavorTestCase


class ROLocalFlavorTests(LocalFlavorTestCase):
    def test_ROCountySelect(self):
        f = ROCountySelect()
        out = u'''<select name="county">
<option value="AB">Alba</option>
<option value="AR">Arad</option>
<option value="AG">Arge\u015f</option>
<option value="BC">Bac\u0103u</option>
<option value="BH">Bihor</option>
<option value="BN">Bistri\u0163a-N\u0103s\u0103ud</option>
<option value="BT">Boto\u015fani</option>
<option value="BV">Bra\u015fov</option>
<option value="BR">Br\u0103ila</option>
<option value="B">Bucure\u015fti</option>
<option value="BZ">Buz\u0103u</option>
<option value="CS">Cara\u015f-Severin</option>
<option value="CL">C\u0103l\u0103ra\u015fi</option>
<option value="CJ" selected="selected">Cluj</option>
<option value="CT">Constan\u0163a</option>
<option value="CV">Covasna</option>
<option value="DB">D\xe2mbovi\u0163a</option>
<option value="DJ">Dolj</option>
<option value="GL">Gala\u0163i</option>
<option value="GR">Giurgiu</option>
<option value="GJ">Gorj</option>
<option value="HR">Harghita</option>
<option value="HD">Hunedoara</option>
<option value="IL">Ialomi\u0163a</option>
<option value="IS">Ia\u015fi</option>
<option value="IF">Ilfov</option>
<option value="MM">Maramure\u015f</option>
<option value="MH">Mehedin\u0163i</option>
<option value="MS">Mure\u015f</option>
<option value="NT">Neam\u0163</option>
<option value="OT">Olt</option>
<option value="PH">Prahova</option>
<option value="SM">Satu Mare</option>
<option value="SJ">S\u0103laj</option>
<option value="SB">Sibiu</option>
<option value="SV">Suceava</option>
<option value="TR">Teleorman</option>
<option value="TM">Timi\u015f</option>
<option value="TL">Tulcea</option>
<option value="VS">Vaslui</option>
<option value="VL">V\xe2lcea</option>
<option value="VN">Vrancea</option>
</select>'''
        self.assertEqual(f.render('county', 'CJ'), out)

    def test_ROCIFField(self):
        error_invalid = [u'Enter a valid CIF.']
        error_atmost = [u'Ensure this value has at most 10 characters (it has 11).']
        error_atleast = [u'Ensure this value has at least 2 characters (it has 1).']
        valid = {
            '21694681': u'21694681',
            'RO21694681': u'21694681',
        }
        invalid = {
            '21694680': error_invalid,
            '21694680000': error_atmost,
            '0': error_atleast,
        }
        self.assertFieldOutput(ROCIFField, valid, invalid)

    def test_ROCNPField(self):
        error_invalid = [u'Enter a valid CNP.']
        error_atleast = [u'Ensure this value has at least 13 characters (it has 10).']
        error_atmost = [u'Ensure this value has at most 13 characters (it has 14).']
        valid = {
            '1981211204489': '1981211204489',
        }
        invalid = {
            '1981211204487': error_invalid,
            '1981232204489': error_invalid,
            '9981211204489': error_invalid,
            '9981211209': error_atleast,
            '19812112044891': error_atmost,
        }
        self.assertFieldOutput(ROCNPField, valid, invalid)

    def test_ROCountyField(self):
        error_format = [u'Enter a Romanian county code or name.']
        valid = {
            'CJ': 'CJ',
            'cj': 'CJ',
            u'Argeş': 'AG',
            u'argeş': 'AG',
        }
        invalid = {
            'Arges': error_format,
        }
        self.assertFieldOutput(ROCountyField, valid, invalid)

    def test_ROIBANField(self):
        error_invalid = [u'Enter a valid IBAN in ROXX-XXXX-XXXX-XXXX-XXXX-XXXX format']
        error_atleast = [u'Ensure this value has at least 24 characters (it has 23).']
        valid = {
            'RO56RZBR0000060003291177': 'RO56RZBR0000060003291177',
            'RO56-RZBR-0000-0600-0329-1177': 'RO56RZBR0000060003291177',
        }
        invalid = {
            'RO56RZBR0000060003291176': error_invalid,
            'AT61 1904 3002 3457 3201': error_invalid,
            'RO56RZBR000006000329117': error_atleast,
        }
        self.assertFieldOutput(ROIBANField, valid, invalid)

    def test_ROPhoneNumberField(self):
        error_format = [u'Phone numbers must be in XXXX-XXXXXX format.']
        error_atleast = [u'Ensure this value has at least 10 characters (it has 9).']
        valid = {
            '0264485936': '0264485936',
            '(0264)-485936': '0264485936',
        }
        invalid = {
            '02644859368': error_format,
            '026448593': error_atleast,
        }
        self.assertFieldOutput(ROPhoneNumberField, valid, invalid)

    def test_ROPostalCodeField(self):
        error_atleast = [u'Ensure this value has at least 6 characters (it has 5).']
        error_atmost = [u'Ensure this value has at most 6 characters (it has 7).']

        valid = {
            '400473': '400473',
        }
        invalid = {
            '40047': error_atleast,
            '4004731': error_atmost,
        }
        self.assertFieldOutput(ROPostalCodeField, valid, invalid)
