# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.contrib.localflavor.mk.forms import (
    MKIdentityCardNumberField, MKMunicipalitySelect, UMCNField)
from django.test import SimpleTestCase

from .forms import MKPersonForm


class MKLocalFlavorTests(SimpleTestCase):

    def setUp(self):
        self.form = MKPersonForm({
            'first_name':'Someone',
            'last_name':'Something',
            'umcn': '2402983450006',
            'municipality':'OD',
            'municipality_req':'VE',
            'id_number':'A1234567',
        })

    def test_get_display_methods(self):
        """
        Test that the get_*_display() methods are added to the model instances.
        """
        person = self.form.save()
        self.assertEqual(person.get_municipality_display(), 'Ohrid')
        self.assertEqual(person.get_municipality_req_display(), 'Veles')

    def test_municipality_required(self):
        """
        Test that required MKMunicipalityFields throw appropriate errors.
        """

        form = MKPersonForm({
            'first_name':'Someone',
            'last_name':'Something',
            'umcn': '2402983450006',
            'municipality':'OD',
            'id_number':'A1234567',
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['municipality_req'], ['This field is required.'])

    def test_umcn_invalid(self):
        """
        Test that UMCNFields throw appropriate errors for invalid UMCNs.
        """
        form = MKPersonForm({
            'first_name':'Someone',
            'last_name':'Something',
            'umcn': '2402983450007',
            'municipality':'OD',
            'municipality_req':'VE',
            'id_number':'A1234567',
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['umcn'], ['The UMCN is not valid.'])

        form = MKPersonForm({
            'first_name':'Someone',
            'last_name':'Something',
            'umcn': '3002983450007',
            'municipality':'OD',
            'municipality_req':'VE',
            'id_number':'A1234567',
        })
        self.assertEqual(form.errors['umcn'],
                ['The first 7 digits of the UMCN must represent a valid past date.'])

    def test_idnumber_invalid(self):
        """
        Test that MKIdentityCardNumberFields throw
        appropriate errors for invalid values
        """

        form = MKPersonForm({
            'first_name':'Someone',
            'last_name':'Something',
            'umcn': '2402983450007',
            'municipality':'OD',
            'municipality_req':'VE',
            'id_number':'A123456a',
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['id_number'],
            ['Identity card numbers must contain either 4 to 7 '
             'digits or an uppercase letter and 7 digits.'])

    def test_field_blank_option(self):
        """
        Test that the empty option is there.
        """
        municipality_select_html = """\
<select name="municipality" id="id_municipality">
<option value="">---------</option>
<option value="AD">Aerodrom</option>
<option value="AR">Aračinovo</option>
<option value="BR">Berovo</option>
<option value="TL">Bitola</option>
<option value="BG">Bogdanci</option>
<option value="VJ">Bogovinje</option>
<option value="BS">Bosilovo</option>
<option value="BN">Brvenica</option>
<option value="BU">Butel</option>
<option value="VA">Valandovo</option>
<option value="VL">Vasilevo</option>
<option value="VV">Vevčani</option>
<option value="VE">Veles</option>
<option value="NI">Vinica</option>
<option value="VC">Vraneštica</option>
<option value="VH">Vrapčište</option>
<option value="GB">Gazi Baba</option>
<option value="GV">Gevgelija</option>
<option value="GT">Gostivar</option>
<option value="GR">Gradsko</option>
<option value="DB">Debar</option>
<option value="DA">Debarca</option>
<option value="DL">Delčevo</option>
<option value="DK">Demir Kapija</option>
<option value="DM">Demir Hisar</option>
<option value="DE">Dolneni</option>
<option value="DR">Drugovo</option>
<option value="GP">Gjorče Petrov</option>
<option value="ZE">Želino</option>
<option value="ZA">Zajas</option>
<option value="ZK">Zelenikovo</option>
<option value="ZR">Zrnovci</option>
<option value="IL">Ilinden</option>
<option value="JG">Jegunovce</option>
<option value="AV">Kavadarci</option>
<option value="KB">Karbinci</option>
<option value="KX">Karpoš</option>
<option value="VD">Kisela Voda</option>
<option value="KH">Kičevo</option>
<option value="KN">Konče</option>
<option value="OC">Koćani</option>
<option value="KY">Kratovo</option>
<option value="KZ">Kriva Palanka</option>
<option value="KG">Krivogaštani</option>
<option value="KS">Kruševo</option>
<option value="UM">Kumanovo</option>
<option value="LI">Lipkovo</option>
<option value="LO">Lozovo</option>
<option value="MR">Mavrovo i Rostuša</option>
<option value="MK">Makedonska Kamenica</option>
<option value="MD">Makedonski Brod</option>
<option value="MG">Mogila</option>
<option value="NG">Negotino</option>
<option value="NV">Novaci</option>
<option value="NS">Novo Selo</option>
<option value="OS">Oslomej</option>
<option value="OD" selected="selected">Ohrid</option>
<option value="PE">Petrovec</option>
<option value="PH">Pehčevo</option>
<option value="PN">Plasnica</option>
<option value="PP">Prilep</option>
<option value="PT">Probištip</option>
<option value="RV">Radoviš</option>
<option value="RN">Rankovce</option>
<option value="RE">Resen</option>
<option value="RO">Rosoman</option>
<option value="AJ">Saraj</option>
<option value="SL">Sveti Nikole</option>
<option value="SS">Sopište</option>
<option value="SD">Star Dojran</option>
<option value="NA">Staro Nagoričane</option>
<option value="UG">Struga</option>
<option value="RU">Strumica</option>
<option value="SU">Studeničani</option>
<option value="TR">Tearce</option>
<option value="ET">Tetovo</option>
<option value="CE">Centar</option>
<option value="CZ">Centar-Župa</option>
<option value="CI">Čair</option>
<option value="CA">Čaška</option>
<option value="CH">Češinovo-Obleševo</option>
<option value="CS">Čučer-Sandevo</option>
<option value="ST">Štip</option>
<option value="SO">Šuto Orizari</option>
</select>"""
        self.assertHTMLEqual(str(self.form['municipality']), municipality_select_html)

    def test_MKIdentityCardNumberField(self):
        error_invalid  = ['Identity card numbers must contain either 4 to 7 '
                          'digits or an uppercase letter and 7 digits.']
        valid = {
            'L0018077':'L0018077',
            'A0078315' : 'A0078315',
        }
        invalid = {
            '123': error_invalid,
            'abcdf': error_invalid,
            '234390a': error_invalid,
        }
        self.assertFieldOutput(MKIdentityCardNumberField, valid, invalid)

    def test_MKMunicipalitySelect(self):
        f = MKMunicipalitySelect()
        out='''<select name="municipality">
<option value="AD">Aerodrom</option>
<option value="AR">Ara\u010dinovo</option>
<option value="BR">Berovo</option>
<option value="TL">Bitola</option>
<option value="BG">Bogdanci</option>
<option value="VJ">Bogovinje</option>
<option value="BS">Bosilovo</option>
<option value="BN">Brvenica</option>
<option value="BU">Butel</option>
<option value="VA">Valandovo</option>
<option value="VL">Vasilevo</option>
<option value="VV">Vev\u010dani</option>
<option value="VE">Veles</option>
<option value="NI">Vinica</option>
<option value="VC">Vrane\u0161tica</option>
<option value="VH">Vrap\u010di\u0161te</option>
<option value="GB">Gazi Baba</option>
<option value="GV">Gevgelija</option>
<option value="GT">Gostivar</option>
<option value="GR">Gradsko</option>
<option value="DB">Debar</option>
<option value="DA">Debarca</option>
<option value="DL" selected="selected">Del\u010devo</option>
<option value="DK">Demir Kapija</option>
<option value="DM">Demir Hisar</option>
<option value="DE">Dolneni</option>
<option value="DR">Drugovo</option>
<option value="GP">Gjor\u010de Petrov</option>
<option value="ZE">\u017delino</option>
<option value="ZA">Zajas</option>
<option value="ZK">Zelenikovo</option>
<option value="ZR">Zrnovci</option>
<option value="IL">Ilinden</option>
<option value="JG">Jegunovce</option>
<option value="AV">Kavadarci</option>
<option value="KB">Karbinci</option>
<option value="KX">Karpo\u0161</option>
<option value="VD">Kisela Voda</option>
<option value="KH">Ki\u010devo</option>
<option value="KN">Kon\u010de</option>
<option value="OC">Ko\u0107ani</option>
<option value="KY">Kratovo</option>
<option value="KZ">Kriva Palanka</option>
<option value="KG">Krivoga\u0161tani</option>
<option value="KS">Kru\u0161evo</option>
<option value="UM">Kumanovo</option>
<option value="LI">Lipkovo</option>
<option value="LO">Lozovo</option>
<option value="MR">Mavrovo i Rostu\u0161a</option>
<option value="MK">Makedonska Kamenica</option>
<option value="MD">Makedonski Brod</option>
<option value="MG">Mogila</option>
<option value="NG">Negotino</option>
<option value="NV">Novaci</option>
<option value="NS">Novo Selo</option>
<option value="OS">Oslomej</option>
<option value="OD">Ohrid</option>
<option value="PE">Petrovec</option>
<option value="PH">Peh\u010devo</option>
<option value="PN">Plasnica</option>
<option value="PP">Prilep</option>
<option value="PT">Probi\u0161tip</option>
<option value="RV">Radovi\u0161</option>
<option value="RN">Rankovce</option>
<option value="RE">Resen</option>
<option value="RO">Rosoman</option>
<option value="AJ">Saraj</option>
<option value="SL">Sveti Nikole</option>
<option value="SS">Sopi\u0161te</option>
<option value="SD">Star Dojran</option>
<option value="NA">Staro Nagori\u010dane</option>
<option value="UG">Struga</option>
<option value="RU">Strumica</option>
<option value="SU">Studeni\u010dani</option>
<option value="TR">Tearce</option>
<option value="ET">Tetovo</option>
<option value="CE">Centar</option>
<option value="CZ">Centar-\u017dupa</option>
<option value="CI">\u010cair</option>
<option value="CA">\u010ca\u0161ka</option>
<option value="CH">\u010ce\u0161inovo-Oble\u0161evo</option>
<option value="CS">\u010cu\u010der-Sandevo</option>
<option value="ST">\u0160tip</option>
<option value="SO">\u0160uto Orizari</option>
</select>'''
        self.assertHTMLEqual(f.render('municipality', 'DL' ), out)

    def test_UMCNField(self):
        error_invalid = ['This field should contain exactly 13 digits.']
        error_checksum = ['The UMCN is not valid.']
        error_date =  ['The first 7 digits of the UMCN '
                       'must represent a valid past date.']
        valid = {
            '2402983450006': '2402983450006',
            '2803984430038': '2803984430038',
            '1909982045004': '1909982045004',
        }
        invalid = {
            '240298345': error_invalid,
            'abcdefghj': error_invalid,
            '2402082450006': error_date,
            '3002982450006': error_date,
            '2402983450007': error_checksum,
            '2402982450006': error_checksum,
        }
        self.assertFieldOutput(UMCNField, valid, invalid)
