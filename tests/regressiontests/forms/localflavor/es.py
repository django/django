from django.contrib.localflavor.es.forms import (ESPostalCodeField, ESPhoneNumberField,
    ESIdentityCardNumberField, ESCCCField, ESRegionSelect, ESProvinceSelect)

from utils import LocalFlavorTestCase


class ESLocalFlavorTests(LocalFlavorTestCase):
    def test_ESRegionSelect(self):
        f = ESRegionSelect()
        out = u'''<select name="regions">
<option value="AN">Andalusia</option>
<option value="AR">Aragon</option>
<option value="O">Principality of Asturias</option>
<option value="IB">Balearic Islands</option>
<option value="PV">Basque Country</option>
<option value="CN">Canary Islands</option>
<option value="S">Cantabria</option>
<option value="CM">Castile-La Mancha</option>
<option value="CL">Castile and Leon</option>
<option value="CT" selected="selected">Catalonia</option>
<option value="EX">Extremadura</option>
<option value="GA">Galicia</option>
<option value="LO">La Rioja</option>
<option value="M">Madrid</option>
<option value="MU">Region of Murcia</option>
<option value="NA">Foral Community of Navarre</option>
<option value="VC">Valencian Community</option>
</select>'''
        self.assertEqual(f.render('regions', 'CT'), out)

    def test_ESProvinceSelect(self):
        f = ESProvinceSelect()
        out = u'''<select name="provinces">
<option value="01">Arava</option>
<option value="02">Albacete</option>
<option value="03">Alacant</option>
<option value="04">Almeria</option>
<option value="05">Avila</option>
<option value="06">Badajoz</option>
<option value="07">Illes Balears</option>
<option value="08" selected="selected">Barcelona</option>
<option value="09">Burgos</option>
<option value="10">Caceres</option>
<option value="11">Cadiz</option>
<option value="12">Castello</option>
<option value="13">Ciudad Real</option>
<option value="14">Cordoba</option>
<option value="15">A Coruna</option>
<option value="16">Cuenca</option>
<option value="17">Girona</option>
<option value="18">Granada</option>
<option value="19">Guadalajara</option>
<option value="20">Guipuzkoa</option>
<option value="21">Huelva</option>
<option value="22">Huesca</option>
<option value="23">Jaen</option>
<option value="24">Leon</option>
<option value="25">Lleida</option>
<option value="26">La Rioja</option>
<option value="27">Lugo</option>
<option value="28">Madrid</option>
<option value="29">Malaga</option>
<option value="30">Murcia</option>
<option value="31">Navarre</option>
<option value="32">Ourense</option>
<option value="33">Asturias</option>
<option value="34">Palencia</option>
<option value="35">Las Palmas</option>
<option value="36">Pontevedra</option>
<option value="37">Salamanca</option>
<option value="38">Santa Cruz de Tenerife</option>
<option value="39">Cantabria</option>
<option value="40">Segovia</option>
<option value="41">Seville</option>
<option value="42">Soria</option>
<option value="43">Tarragona</option>
<option value="44">Teruel</option>
<option value="45">Toledo</option>
<option value="46">Valencia</option>
<option value="47">Valladolid</option>
<option value="48">Bizkaia</option>
<option value="49">Zamora</option>
<option value="50">Zaragoza</option>
<option value="51">Ceuta</option>
<option value="52">Melilla</option>
</select>'''
        self.assertEqual(f.render('provinces', '08'), out)

    def test_ESPostalCodeField(self):
        error_invalid = [u'Enter a valid postal code in the range and format 01XXX - 52XXX.']
        valid = {
            '08028': '08028',
            '28080': '28080',
        }
        invalid = {
            '53001': error_invalid,
            '0801': error_invalid,
            '080001': error_invalid,
            '00999': error_invalid,
            '08 01': error_invalid,
            '08A01': error_invalid,
        }
        self.assertFieldOutput(ESPostalCodeField, valid, invalid)

    def test_ESPhoneNumberField(self):
        error_invalid = [u'Enter a valid phone number in one of the formats 6XXXXXXXX, 8XXXXXXXX or 9XXXXXXXX.']
        valid = {
            '650010101': '650010101',
            '931234567': '931234567',
            '800123123': '800123123',
        }
        invalid = {
            '555555555': error_invalid,
            '789789789': error_invalid,
            '99123123': error_invalid,
            '9999123123': error_invalid,
        }
        self.assertFieldOutput(ESPhoneNumberField, valid, invalid)

    def test_ESIdentityCardNumberField(self):
        error_invalid = [u'Please enter a valid NIF, NIE, or CIF.']
        error_checksum_nif = [u'Invalid checksum for NIF.']
        error_checksum_nie = [u'Invalid checksum for NIE.']
        error_checksum_cif = [u'Invalid checksum for CIF.']
        valid = {
            '78699688J': '78699688J',
            '78699688-J': '78699688J',
            '78699688 J': '78699688J',
            '78699688 j': '78699688J',
            'X0901797J': 'X0901797J',
            'X-6124387-Q': 'X6124387Q',
            'X 0012953 G': 'X0012953G',
            'x-3287690-r': 'X3287690R',
            't-03287690r': 'T03287690R',
            'P2907500I': 'P2907500I',
            'B38790911': 'B38790911',
            'B31234560': 'B31234560',
            'B-3879091A': 'B3879091A',
            'B 38790911': 'B38790911',
            'P-3900800-H': 'P3900800H',
            'P 39008008': 'P39008008',
            'C-28795565': 'C28795565',
            'C 2879556E': 'C2879556E',
        }
        invalid = {
            '78699688T': error_checksum_nif,
            'X-03287690': error_invalid,
            'X-03287690-T': error_checksum_nie,
            'B 38790917': error_checksum_cif,
            'C28795567': error_checksum_cif,
            'I38790911': error_invalid,
            '78699688-2': error_invalid,
        }
        self.assertFieldOutput(ESIdentityCardNumberField, valid, invalid)
    
    def test_ESCCCField(self):
        error_invalid = [u'Please enter a valid bank account number in format XXXX-XXXX-XX-XXXXXXXXXX.']
        error_checksum = [u'Invalid checksum for bank account number.']
        valid = {
            '20770338793100254321': '20770338793100254321',
            '2077 0338 79 3100254321': '2077 0338 79 3100254321',
            '2077-0338-79-3100254321': '2077-0338-79-3100254321',
        }
        invalid = {
            '2077.0338.79.3100254321': error_invalid,
            '2077-0338-78-3100254321': error_checksum,
            '2077-0338-89-3100254321': error_checksum,
            '2077-03-3879-3100254321': error_invalid,
        }
        self.assertFieldOutput(ESCCCField, valid, invalid)


