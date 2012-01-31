import warnings

from django.contrib.localflavor.id.forms import (IDPhoneNumberField,
    IDPostCodeField, IDNationalIdentityNumberField, IDLicensePlateField,
    IDProvinceSelect, IDLicensePlatePrefixSelect)

from django.test import SimpleTestCase


class IDLocalFlavorTests(SimpleTestCase):
    def setUp(self):
        self.save_warnings_state()
        warnings.filterwarnings(
            "ignore",
            category=RuntimeWarning,
            module='django.contrib.localflavor.id.id_choices'
        )

    def tearDown(self):
        self.restore_warnings_state()

    def test_IDProvinceSelect(self):
        f = IDProvinceSelect()
        out = u'''<select name="provinces">
<option value="ACE">Aceh</option>
<option value="BLI">Bali</option>
<option value="BTN">Banten</option>
<option value="BKL">Bengkulu</option>
<option value="DIY">Yogyakarta</option>
<option value="JKT">Jakarta</option>
<option value="GOR">Gorontalo</option>
<option value="JMB">Jambi</option>
<option value="JBR">Jawa Barat</option>
<option value="JTG">Jawa Tengah</option>
<option value="JTM">Jawa Timur</option>
<option value="KBR">Kalimantan Barat</option>
<option value="KSL">Kalimantan Selatan</option>
<option value="KTG">Kalimantan Tengah</option>
<option value="KTM">Kalimantan Timur</option>
<option value="BBL">Kepulauan Bangka-Belitung</option>
<option value="KRI">Kepulauan Riau</option>
<option value="LPG" selected="selected">Lampung</option>
<option value="MLK">Maluku</option>
<option value="MUT">Maluku Utara</option>
<option value="NTB">Nusa Tenggara Barat</option>
<option value="NTT">Nusa Tenggara Timur</option>
<option value="PPA">Papua</option>
<option value="PPB">Papua Barat</option>
<option value="RIU">Riau</option>
<option value="SLB">Sulawesi Barat</option>
<option value="SLS">Sulawesi Selatan</option>
<option value="SLT">Sulawesi Tengah</option>
<option value="SLR">Sulawesi Tenggara</option>
<option value="SLU">Sulawesi Utara</option>
<option value="SMB">Sumatera Barat</option>
<option value="SMS">Sumatera Selatan</option>
<option value="SMU">Sumatera Utara</option>
</select>'''
        self.assertHTMLEqual(f.render('provinces', 'LPG'), out)

    def test_IDLicensePlatePrefixSelect(self):
        f = IDLicensePlatePrefixSelect()
        out = u'''<select name="codes">
<option value="A">Banten</option>
<option value="AA">Magelang</option>
<option value="AB">Yogyakarta</option>
<option value="AD">Surakarta - Solo</option>
<option value="AE">Madiun</option>
<option value="AG">Kediri</option>
<option value="B">Jakarta</option>
<option value="BA">Sumatera Barat</option>
<option value="BB">Tapanuli</option>
<option value="BD">Bengkulu</option>
<option value="BE" selected="selected">Lampung</option>
<option value="BG">Sumatera Selatan</option>
<option value="BH">Jambi</option>
<option value="BK">Sumatera Utara</option>
<option value="BL">Nanggroe Aceh Darussalam</option>
<option value="BM">Riau</option>
<option value="BN">Kepulauan Bangka Belitung</option>
<option value="BP">Kepulauan Riau</option>
<option value="CC">Corps Consulate</option>
<option value="CD">Corps Diplomatic</option>
<option value="D">Bandung</option>
<option value="DA">Kalimantan Selatan</option>
<option value="DB">Sulawesi Utara Daratan</option>
<option value="DC">Sulawesi Barat</option>
<option value="DD">Sulawesi Selatan</option>
<option value="DE">Maluku</option>
<option value="DG">Maluku Utara</option>
<option value="DH">NTT - Timor</option>
<option value="DK">Bali</option>
<option value="DL">Sulawesi Utara Kepulauan</option>
<option value="DM">Gorontalo</option>
<option value="DN">Sulawesi Tengah</option>
<option value="DR">NTB - Lombok</option>
<option value="DS">Papua dan Papua Barat</option>
<option value="DT">Sulawesi Tenggara</option>
<option value="E">Cirebon</option>
<option value="EA">NTB - Sumbawa</option>
<option value="EB">NTT - Flores</option>
<option value="ED">NTT - Sumba</option>
<option value="F">Bogor</option>
<option value="G">Pekalongan</option>
<option value="H">Semarang</option>
<option value="K">Pati</option>
<option value="KB">Kalimantan Barat</option>
<option value="KH">Kalimantan Tengah</option>
<option value="KT">Kalimantan Timur</option>
<option value="L">Surabaya</option>
<option value="M">Madura</option>
<option value="N">Malang</option>
<option value="P">Jember</option>
<option value="R">Banyumas</option>
<option value="RI">Federal Government</option>
<option value="S">Bojonegoro</option>
<option value="T">Purwakarta</option>
<option value="W">Sidoarjo</option>
<option value="Z">Garut</option>
</select>'''
        self.assertHTMLEqual(f.render('codes', 'BE'), out)

    def test_IDPhoneNumberField(self):
        error_invalid = [u'Enter a valid phone number']
        valid = {
            '0812-3456789': u'0812-3456789',
            '081234567890': u'081234567890',
            '021 345 6789': u'021 345 6789',
            '0213456789': u'0213456789',
            '+62-21-3456789': u'+62-21-3456789',
            '(021) 345 6789': u'(021) 345 6789',
        }
        invalid = {
            '0123456789': error_invalid,
            '+62-021-3456789': error_invalid,
            '+62-0812-3456789': error_invalid,
            '0812345678901': error_invalid,
            'foo': error_invalid,
        }
        self.assertFieldOutput(IDPhoneNumberField, valid, invalid)

    def test_IDPostCodeField(self):
        error_invalid = [u'Enter a valid post code']
        valid = {
            '12340': u'12340',
            '25412': u'25412',
            ' 12340 ': u'12340',
        }
        invalid = {
            '12 3 4 0': error_invalid,
            '12345': error_invalid,
            '10100': error_invalid,
            '123456': error_invalid,
            'foo': error_invalid,
        }
        self.assertFieldOutput(IDPostCodeField, valid, invalid)

    def test_IDNationalIdentityNumberField(self):
        error_invalid = [u'Enter a valid NIK/KTP number']
        valid = {
            ' 12.3456.010178 3456 ': u'12.3456.010178.3456',
            '1234560101783456': u'12.3456.010178.3456',
            '12.3456.010101.3456': u'12.3456.010101.3456',
        }
        invalid = {
            '12.3456.310278.3456': error_invalid,
            '00.0000.010101.0000': error_invalid,
            '1234567890123456': error_invalid,
            'foo': error_invalid,
        }
        self.assertFieldOutput(IDNationalIdentityNumberField, valid, invalid)

    def test_IDLicensePlateField(self):
        error_invalid = [u'Enter a valid vehicle license plate number']
        valid = {
            ' b 1234  ab ': u'B 1234 AB',
            'B 1234 ABC': u'B 1234 ABC',
            'A 12': u'A 12',
            'DK 12345 12': u'DK 12345 12',
            'RI 10': u'RI 10',
            'CD 12 12': u'CD 12 12',
        }
        invalid = {
            'CD 10 12': error_invalid,
            'CD 1234 12': error_invalid,
            'RI 10 AB': error_invalid,
            'B 12345 01': error_invalid,
            'N 1234 12': error_invalid,
            'A 12 XYZ': error_invalid,
            'Q 1234 AB': error_invalid,
            'foo': error_invalid,
        }
        self.assertFieldOutput(IDLicensePlateField, valid, invalid)
