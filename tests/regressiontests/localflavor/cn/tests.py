# Tests for contrib/localflavor/ CN Form Fields

from django.contrib.localflavor.cn.forms import (CNProvinceSelect,
        CNPostCodeField, CNIDCardField, CNPhoneNumberField, CNCellNumberField)
from django.test import SimpleTestCase

class CNLocalFlavorTests(SimpleTestCase):
    def test_CNProvinceSelect(self):
        f = CNProvinceSelect()
        correct_output = u'''<select name="provinces">
<option value="anhui">\u5b89\u5fbd</option>
<option value="beijing">\u5317\u4eac</option>
<option value="chongqing">\u91cd\u5e86</option>
<option value="fujian">\u798f\u5efa</option>
<option value="gansu">\u7518\u8083</option>
<option value="guangdong">\u5e7f\u4e1c</option>
<option value="guangxi">\u5e7f\u897f\u58ee\u65cf\u81ea\u6cbb\u533a</option>
<option value="guizhou">\u8d35\u5dde</option>
<option value="hainan">\u6d77\u5357</option>
<option value="hebei">\u6cb3\u5317</option>
<option value="heilongjiang">\u9ed1\u9f99\u6c5f</option>
<option value="henan">\u6cb3\u5357</option>
<option value="hongkong">\u9999\u6e2f</option>
<option value="hubei" selected="selected">\u6e56\u5317</option>
<option value="hunan">\u6e56\u5357</option>
<option value="jiangsu">\u6c5f\u82cf</option>
<option value="jiangxi">\u6c5f\u897f</option>
<option value="jilin">\u5409\u6797</option>
<option value="liaoning">\u8fbd\u5b81</option>
<option value="macao">\u6fb3\u95e8</option>
<option value="neimongol">\u5185\u8499\u53e4\u81ea\u6cbb\u533a</option>
<option value="ningxia">\u5b81\u590f\u56de\u65cf\u81ea\u6cbb\u533a</option>
<option value="qinghai">\u9752\u6d77</option>
<option value="shaanxi">\u9655\u897f</option>
<option value="shandong">\u5c71\u4e1c</option>
<option value="shanghai">\u4e0a\u6d77</option>
<option value="shanxi">\u5c71\u897f</option>
<option value="sichuan">\u56db\u5ddd</option>
<option value="taiwan">\u53f0\u6e7e</option>
<option value="tianjin">\u5929\u6d25</option>
<option value="xinjiang">\u65b0\u7586\u7ef4\u543e\u5c14\u81ea\u6cbb\u533a</option>
<option value="xizang">\u897f\u85cf\u81ea\u6cbb\u533a</option>
<option value="yunnan">\u4e91\u5357</option>
<option value="zhejiang">\u6d59\u6c5f</option>
</select>'''
        self.assertHTMLEqual(f.render('provinces', 'hubei'), correct_output)

    def test_CNPostCodeField(self):
        error_format = [u'Enter a post code in the format XXXXXX.']
        valid = {
                '091209': u'091209'
        }
        invalid = {
                '09120': error_format,
                '09120916': error_format
        }
        self.assertFieldOutput(CNPostCodeField, valid, invalid)

    def test_CNIDCardField(self):
        valid = {
                # A valid 1st generation ID Card Number.
                '110101491001001': u'110101491001001',
                # A valid 2nd generation ID Card number.
                '11010119491001001X': u'11010119491001001X',
                # Another valid 2nd gen ID Number with a case change
                '11010119491001001x': u'11010119491001001X'
        }

        wrong_format = [u'ID Card Number consists of 15 or 18 digits.']
        wrong_location = [u'Invalid ID Card Number: Wrong location code']
        wrong_bday = [u'Invalid ID Card Number: Wrong birthdate']
        wrong_checksum = [u'Invalid ID Card Number: Wrong checksum']

        invalid = {
                'abcdefghijklmnop': wrong_format,
                '1010101010101010': wrong_format,
                '010101491001001' : wrong_location, # 1st gen, 01 is invalid
                '110101491041001' : wrong_bday, # 1st gen. There wasn't day 41
                '92010119491001001X': wrong_location, # 2nd gen, 92 is invalid
                '91010119491301001X': wrong_bday, # 2nd gen, 19491301 is invalid date
                '910101194910010014': wrong_checksum #2nd gen
        }
        self.assertFieldOutput(CNIDCardField, valid, invalid)

    def test_CNPhoneNumberField(self):
        error_format = [u'Enter a valid phone number.']
        valid = {
                '010-12345678': u'010-12345678',
                '010-1234567': u'010-1234567',
                '0101-12345678': u'0101-12345678',
                '0101-1234567': u'0101-1234567',
                '010-12345678-020':u'010-12345678-020'
        }
        invalid = {
                '01x-12345678': error_format,
                '12345678': error_format,
                '01123-12345678': error_format,
                '010-123456789': error_format,
                '010-12345678-': error_format
        }
        self.assertFieldOutput(CNPhoneNumberField, valid, invalid)

    def test_CNCellNumberField(self):
        error_format = [u'Enter a valid cell number.']
        valid = {
                '13012345678': u'13012345678',
        }
        invalid = {
                '130123456789': error_format,
                '14012345678': error_format
        }
        self.assertFieldOutput(CNCellNumberField, valid, invalid)
