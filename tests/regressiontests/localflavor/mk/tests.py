from django.test import TestCase
from forms import MKPersonForm

class MKLocalflavorTests(TestCase):
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
            form.errors['municipality_req'], [u'This field is required.'])

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
        self.assertEqual(form.errors['umcn'], [u'The UMCN is not valid.'])

        form = MKPersonForm({
            'first_name':'Someone',
            'last_name':'Something',
            'umcn': '3002983450007',
            'municipality':'OD',
            'municipality_req':'VE',
            'id_number':'A1234567',
        })
        self.assertEqual(form.errors['umcn'],
                [u'The first 7 digits of the UMCN must represent a valid past date.'])

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
            [u'Identity card numbers must contain either 4 to 7 '
              'digits or an uppercase letter and 7 digits.'])

    def test_field_blank_option(self):
        """
        Test that the empty option is there.
        """
        municipality_select_html = """\
<select name="municipality" id="id_municipality">
<option value="">---------</option>
<option value="AD">Aerodrom</option>
<option value="AR">Ara\xc4\x8dinovo</option>
<option value="BR">Berovo</option>
<option value="TL">Bitola</option>
<option value="BG">Bogdanci</option>
<option value="VJ">Bogovinje</option>
<option value="BS">Bosilovo</option>
<option value="BN">Brvenica</option>
<option value="BU">Butel</option>
<option value="VA">Valandovo</option>
<option value="VL">Vasilevo</option>
<option value="VV">Vev\xc4\x8dani</option>
<option value="VE">Veles</option>
<option value="NI">Vinica</option>
<option value="VC">Vrane\xc5\xa1tica</option>
<option value="VH">Vrap\xc4\x8di\xc5\xa1te</option>
<option value="GB">Gazi Baba</option>
<option value="GV">Gevgelija</option>
<option value="GT">Gostivar</option>
<option value="GR">Gradsko</option>
<option value="DB">Debar</option>
<option value="DA">Debarca</option>
<option value="DL">Del\xc4\x8devo</option>
<option value="DK">Demir Kapija</option>
<option value="DM">Demir Hisar</option>
<option value="DE">Dolneni</option>
<option value="DR">Drugovo</option>
<option value="GP">Gjor\xc4\x8de Petrov</option>
<option value="ZE">\xc5\xbdelino</option>
<option value="ZA">Zajas</option>
<option value="ZK">Zelenikovo</option>
<option value="ZR">Zrnovci</option>
<option value="IL">Ilinden</option>
<option value="JG">Jegunovce</option>
<option value="AV">Kavadarci</option>
<option value="KB">Karbinci</option>
<option value="KX">Karpo\xc5\xa1</option>
<option value="VD">Kisela Voda</option>
<option value="KH">Ki\xc4\x8devo</option>
<option value="KN">Kon\xc4\x8de</option>
<option value="OC">Ko\xc4\x87ani</option>
<option value="KY">Kratovo</option>
<option value="KZ">Kriva Palanka</option>
<option value="KG">Krivoga\xc5\xa1tani</option>
<option value="KS">Kru\xc5\xa1evo</option>
<option value="UM">Kumanovo</option>
<option value="LI">Lipkovo</option>
<option value="LO">Lozovo</option>
<option value="MR">Mavrovo i Rostu\xc5\xa1a</option>
<option value="MK">Makedonska Kamenica</option>
<option value="MD">Makedonski Brod</option>
<option value="MG">Mogila</option>
<option value="NG">Negotino</option>
<option value="NV">Novaci</option>
<option value="NS">Novo Selo</option>
<option value="OS">Oslomej</option>
<option value="OD" selected="selected">Ohrid</option>
<option value="PE">Petrovec</option>
<option value="PH">Peh\xc4\x8devo</option>
<option value="PN">Plasnica</option>
<option value="PP">Prilep</option>
<option value="PT">Probi\xc5\xa1tip</option>
<option value="RV">Radovi\xc5\xa1</option>
<option value="RN">Rankovce</option>
<option value="RE">Resen</option>
<option value="RO">Rosoman</option>
<option value="AJ">Saraj</option>
<option value="SL">Sveti Nikole</option>
<option value="SS">Sopi\xc5\xa1te</option>
<option value="SD">Star Dojran</option>
<option value="NA">Staro Nagori\xc4\x8dane</option>
<option value="UG">Struga</option>
<option value="RU">Strumica</option>
<option value="SU">Studeni\xc4\x8dani</option>
<option value="TR">Tearce</option>
<option value="ET">Tetovo</option>
<option value="CE">Centar</option>
<option value="CZ">Centar-\xc5\xbdupa</option>
<option value="CI">\xc4\x8cair</option>
<option value="CA">\xc4\x8ca\xc5\xa1ka</option>
<option value="CH">\xc4\x8ce\xc5\xa1inovo-Oble\xc5\xa1evo</option>
<option value="CS">\xc4\x8cu\xc4\x8der-Sandevo</option>
<option value="ST">\xc5\xa0tip</option>
<option value="SO">\xc5\xa0uto Orizari</option>
</select>"""
        self.assertEqual(str(self.form['municipality']), municipality_select_html)
