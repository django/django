# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ RO form fields.

tests = r"""
>>> from django.contrib.localflavor.ro.forms import *

##ROCIFField ################################################################

f = ROCIFField()
f.clean('21694681')
u'21694681'
f.clean('RO21694681')
u'21694681'
f.clean('21694680')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CIF']
f.clean('21694680000')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 10 characters (it has 11).']
f.clean('0')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 2 characters (it has 1).']
f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

##ROCNPField #################################################################

f = ROCNPField()
f.clean('1981211204489')
u'1981211204489'
f.clean('1981211204487')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CNP']
f.clean('1981232204489')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CNP']
f.clean('9981211204489')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CNP']
f.clean('9981211209')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 13 characters (it has 10).']
f.clean('19812112044891')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 13 characters (it has 14).']
f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

##ROCountyField ##############################################################

f = ROCountyField()
f.clean('CJ')
'CJ'
f.clean('cj')
'CJ'
f.clean('Argeş')
'AG'
f.clean('argeş')
'AG'
f.clean('Arges')
Traceback (most recent call last):
...
ValidationError: [u'Enter a Romanian county code or name.']
f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

##ROCountySelect #############################################################

f = ROCountySelect()
f.render('county','CJ')
u'<select name="county">\n<option value="AB">Alba</option>\n<option value="AR">A
rad</option>\n<option value="AG">Arge\u015f</option>\n<option value="BC">Bac\u01
03u</option>\n<option value="BH">Bihor</option>\n<option value="BN">Bistri\u0163
a-N\u0103s\u0103ud</option>\n<option value="BT">Boto\u015fani</option>\n<option
value="BV">Bra\u015fov</option>\n<option value="BR">Br\u0103ila</option>\n<optio
n value="B">Bucure\u015fti</option>\n<option value="BZ">Buz\u0103u</option>\n<op
tion value="CS">Cara\u015f-Severin</option>\n<option value="CL">C\u0103l\u0103ra
\u015fi</option>\n<option value="CJ" selected="selected">Cluj</option>\n<option
value="CT">Constan\u0163a</option>\n<option value="CV">Covasna</option>\n<option
 value="DB">D\xe2mbovi\u0163a</option>\n<option value="DJ">Dolj</option>\n<optio
n value="GL">Gala\u0163i</option>\n<option value="GR">Giurgiu</option>\n<option
value="GJ">Gorj</option>\n<option value="HR">Harghita</option>\n<option value="H
D">Hunedoara</option>\n<option value="IL">Ialomi\u0163a</option>\n<option value=
"IS">Ia\u015fi</option>\n<option value="IF">Ilfov</option>\n<option value="MM">M
aramure\u015f</option>\n<option value="MH">Mehedin\u0163i</option>\n<option valu
e="MS">Mure\u015f</option>\n<option value="NT">Neam\u0163</option>\n<option valu
e="OT">Olt</option>\n<option value="PH">Prahova</option>\n<option value="SM">Sat
u Mare</option>\n<option value="SJ">S\u0103laj</option>\n<option value="SB">Sibi
u</option>\n<option value="SV">Suceava</option>\n<option value="TR">Teleorman</o
ption>\n<option value="TM">Timi\u015f</option>\n<option value="TL">Tulcea</optio
n>\n<option value="VS">Vaslui</option>\n<option value="VL">V\xe2lcea</option>\n<
option value="VN">Vrancea</option>\n</select>'

##ROIBANField #################################################################

f = ROIBANField()
f.clean('RO56RZBR0000060003291177')
u'RO56RZBR0000060003291177'
f.clean('RO56RZBR0000060003291176')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid IBAN in ROXX-XXXX-XXXX-XXXX-XXXX-XXXX format']

f.clean('RO56-RZBR-0000-0600-0329-1177')
u'RO56RZBR0000060003291177'
f.clean('AT61 1904 3002 3457 3201')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid IBAN in ROXX-XXXX-XXXX-XXXX-XXXX-XXXX format']

f.clean('RO56RZBR000006000329117')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 24 characters (it has 23).']
f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

##ROPhoneNumberField ##########################################################

f = ROPhoneNumberField()
f.clean('0264485936')
u'0264485936'
f.clean('(0264)-485936')
u'0264485936'
f.clean('02644859368')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXXX-XXXXXX format.']
f.clean('026448593')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 10 characters (it has 9).']
f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

##ROPostalCodeField ###########################################################

f = ROPostalCodeField()
f.clean('400473')
u'400473'
f.clean('40047')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 6 characters (it has 5).']
f.clean('4004731')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 6 characters (it has 7).']
f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
"""
