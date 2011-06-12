from django.contrib.localflavor.mk.forms import (
    MKIdentityCardNumberField, MKMunicipalitySelect, UMCNField)

from utils import LocalFlavorTestCase


class MKLocalFlavorTests(LocalFlavorTestCase):

    def test_MKIdentityCardNumberField(self):
        error_invalid  = [u'Identity card numbers must contain either 4 to 7 '
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
        out=u'''<select name="municipality">
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
        self.assertEqual(f.render('municipality', 'DL' ), out)

    def test_UMCNField(self):
        error_invalid = [u'This field should contain exactly 13 digits.']
        error_checksum = [u'The UMCN is not valid.']
        error_date =  [u'The first 7 digits of the UMCN '
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
