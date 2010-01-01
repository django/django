# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ ID form fields.

tests = r"""

# IDPhoneNumberField ########################################################

>>> from django.contrib.localflavor.id.forms import IDPhoneNumberField
>>> f = IDPhoneNumberField(required=False)
>>> f.clean('')
u''
>>> f.clean('0812-3456789')
u'0812-3456789'
>>> f.clean('081234567890')
u'081234567890'
>>> f.clean('021 345 6789')
u'021 345 6789'
>>> f.clean('0213456789')
u'0213456789'
>>> f.clean('0123456789')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid phone number']
>>> f.clean('+62-21-3456789')
u'+62-21-3456789'
>>> f.clean('+62-021-3456789')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid phone number']
>>> f.clean('(021) 345 6789')
u'(021) 345 6789'
>>> f.clean('+62-021-3456789')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid phone number']
>>> f.clean('+62-0812-3456789')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid phone number']
>>> f.clean('0812345678901')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid phone number']
>>> f.clean('foo')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid phone number']

# IDPostCodeField ############################################################

>>> from django.contrib.localflavor.id.forms import IDPostCodeField
>>> f = IDPostCodeField(required=False)
>>> f.clean('')
u''
>>> f.clean('12340')
u'12340'
>>> f.clean('25412')
u'25412'
>>> f.clean(' 12340 ')
u'12340'
>>> f.clean('12 3 4 0')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid post code']
>>> f.clean('12345')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid post code']
>>> f.clean('10100')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid post code']
>>> f.clean('123456')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid post code']
>>> f.clean('foo')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid post code']

# IDNationalIdentityNumberField #########################################################

>>> from django.contrib.localflavor.id.forms import IDNationalIdentityNumberField
>>> f = IDNationalIdentityNumberField(required=False)
>>> f.clean('')
u''
>>> f.clean(' 12.3456.010178 3456 ')
u'12.3456.010178.3456'
>>> f.clean('1234560101783456')
u'12.3456.010178.3456'
>>> f.clean('12.3456.010101.3456')
u'12.3456.010101.3456'
>>> f.clean('12.3456.310278.3456')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid NIK/KTP number']
>>> f.clean('00.0000.010101.0000')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid NIK/KTP number']
>>> f.clean('1234567890123456')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid NIK/KTP number']
>>> f.clean('foo')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid NIK/KTP number']

# IDProvinceSelect ##########################################################

>>> from django.contrib.localflavor.id.forms import IDProvinceSelect
>>> s = IDProvinceSelect()
>>> s.render('provinces', 'LPG')
u'<select name="provinces">\n<option value="BLI">Bali</option>\n<option value="BTN">Banten</option>\n<option value="BKL">Bengkulu</option>\n<option value="DIY">Yogyakarta</option>\n<option value="JKT">Jakarta</option>\n<option value="GOR">Gorontalo</option>\n<option value="JMB">Jambi</option>\n<option value="JBR">Jawa Barat</option>\n<option value="JTG">Jawa Tengah</option>\n<option value="JTM">Jawa Timur</option>\n<option value="KBR">Kalimantan Barat</option>\n<option value="KSL">Kalimantan Selatan</option>\n<option value="KTG">Kalimantan Tengah</option>\n<option value="KTM">Kalimantan Timur</option>\n<option value="BBL">Kepulauan Bangka-Belitung</option>\n<option value="KRI">Kepulauan Riau</option>\n<option value="LPG" selected="selected">Lampung</option>\n<option value="MLK">Maluku</option>\n<option value="MUT">Maluku Utara</option>\n<option value="NAD">Nanggroe Aceh Darussalam</option>\n<option value="NTB">Nusa Tenggara Barat</option>\n<option value="NTT">Nusa Tenggara Timur</option>\n<option value="PPA">Papua</option>\n<option value="PPB">Papua Barat</option>\n<option value="RIU">Riau</option>\n<option value="SLB">Sulawesi Barat</option>\n<option value="SLS">Sulawesi Selatan</option>\n<option value="SLT">Sulawesi Tengah</option>\n<option value="SLR">Sulawesi Tenggara</option>\n<option value="SLU">Sulawesi Utara</option>\n<option value="SMB">Sumatera Barat</option>\n<option value="SMS">Sumatera Selatan</option>\n<option value="SMU">Sumatera Utara</option>\n</select>'

# IDLicensePlatePrefixelect ########################################################################

>>> from django.contrib.localflavor.id.forms import IDLicensePlatePrefixSelect
>>> s = IDLicensePlatePrefixSelect()
>>> s.render('codes', 'BE')
u'<select name="codes">\n<option value="A">Banten</option>\n<option value="AA">Magelang</option>\n<option value="AB">Yogyakarta</option>\n<option value="AD">Surakarta - Solo</option>\n<option value="AE">Madiun</option>\n<option value="AG">Kediri</option>\n<option value="B">Jakarta</option>\n<option value="BA">Sumatera Barat</option>\n<option value="BB">Tapanuli</option>\n<option value="BD">Bengkulu</option>\n<option value="BE" selected="selected">Lampung</option>\n<option value="BG">Sumatera Selatan</option>\n<option value="BH">Jambi</option>\n<option value="BK">Sumatera Utara</option>\n<option value="BL">Nanggroe Aceh Darussalam</option>\n<option value="BM">Riau</option>\n<option value="BN">Kepulauan Bangka Belitung</option>\n<option value="BP">Kepulauan Riau</option>\n<option value="CC">Corps Consulate</option>\n<option value="CD">Corps Diplomatic</option>\n<option value="D">Bandung</option>\n<option value="DA">Kalimantan Selatan</option>\n<option value="DB">Sulawesi Utara Daratan</option>\n<option value="DC">Sulawesi Barat</option>\n<option value="DD">Sulawesi Selatan</option>\n<option value="DE">Maluku</option>\n<option value="DG">Maluku Utara</option>\n<option value="DH">NTT - Timor</option>\n<option value="DK">Bali</option>\n<option value="DL">Sulawesi Utara Kepulauan</option>\n<option value="DM">Gorontalo</option>\n<option value="DN">Sulawesi Tengah</option>\n<option value="DR">NTB - Lombok</option>\n<option value="DS">Papua dan Papua Barat</option>\n<option value="DT">Sulawesi Tenggara</option>\n<option value="E">Cirebon</option>\n<option value="EA">NTB - Sumbawa</option>\n<option value="EB">NTT - Flores</option>\n<option value="ED">NTT - Sumba</option>\n<option value="F">Bogor</option>\n<option value="G">Pekalongan</option>\n<option value="H">Semarang</option>\n<option value="K">Pati</option>\n<option value="KB">Kalimantan Barat</option>\n<option value="KH">Kalimantan Tengah</option>\n<option value="KT">Kalimantan Timur</option>\n<option value="L">Surabaya</option>\n<option value="M">Madura</option>\n<option value="N">Malang</option>\n<option value="P">Jember</option>\n<option value="R">Banyumas</option>\n<option value="RI">Federal Government</option>\n<option value="S">Bojonegoro</option>\n<option value="T">Purwakarta</option>\n<option value="W">Sidoarjo</option>\n<option value="Z">Garut</option>\n</select>'

# IDLicensePlateField #######################################################################

>>> from django.contrib.localflavor.id.forms import IDLicensePlateField
>>> f = IDLicensePlateField(required=False)
>>> f.clean('')
u''
>>> f.clean(' b 1234  ab ')
u'B 1234 AB'
>>> f.clean('B 1234 ABC')
u'B 1234 ABC'
>>> f.clean('A 12')
u'A 12'
>>> f.clean('DK 12345 12')
u'DK 12345 12'
>>> f.clean('RI 10')
u'RI 10'
>>> f.clean('CD 12 12')
u'CD 12 12'
>>> f.clean('CD 10 12')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid vehicle license plate number']
>>> f.clean('CD 1234 12')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid vehicle license plate number']
>>> f.clean('RI 10 AB')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid vehicle license plate number']
>>> f.clean('B 12345 01')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid vehicle license plate number']
>>> f.clean('N 1234 12')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid vehicle license plate number']
>>> f.clean('A 12 XYZ')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid vehicle license plate number']
>>> f.clean('Q 1234 AB')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid vehicle license plate number']
>>> f.clean('foo')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid vehicle license plate number']
"""