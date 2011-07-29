# -*- coding: utf-8 -*-
from django.test import TestCase
from forms import MXPersonProfileForm

class MXLocalFlavorTests(TestCase):
    def setUp(self):
        self.form = MXPersonProfileForm({
            'state': 'MIC',
            'rfc': 'toma880125kv3',
            'curp': 'toma880125hmnrrn02',
            'zip_code': '58120',
        })

    def test_get_display_methods(self):
        """Test that the get_*_display() methods are added to the model instances."""
        place = self.form.save()
        self.assertEqual(place.get_state_display(), u'Michoacán')

    def test_errors(self):
        """Test that required MXFields throw appropriate errors."""
        form = MXPersonProfileForm({
            'state': 'Invalid state',
            'rfc': 'invalid rfc',
            'curp': 'invalid curp',
            'zip_code': 'xxx',
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['state'], [u'Select a valid choice. Invalid state is not one of the available choices.'])
        self.assertEqual(form.errors['rfc'], [u'Enter a valid RFC.'])
        self.assertEqual(form.errors['curp'], [u'Ensure this value has at least 18 characters (it has 12).', u'Enter a valid CURP.'])
        self.assertEqual(form.errors['zip_code'], [u'Enter a valid zip code in the format XXXXX.'])

    def test_field_blank_option(self):
        """Test that the empty option is there."""
        state_select_html = """\
<select name="state" id="id_state">
<option value="">---------</option>
<option value="AGU">Aguascalientes</option>
<option value="BCN">Baja California</option>
<option value="BCS">Baja California Sur</option>
<option value="CAM">Campeche</option>
<option value="CHH">Chihuahua</option>
<option value="CHP">Chiapas</option>
<option value="COA">Coahuila</option>
<option value="COL">Colima</option>
<option value="DIF">Distrito Federal</option>
<option value="DUR">Durango</option>
<option value="GRO">Guerrero</option>
<option value="GUA">Guanajuato</option>
<option value="HID">Hidalgo</option>
<option value="JAL">Jalisco</option>
<option value="MEX">Estado de México</option>
<option value="MIC" selected="selected">Michoacán</option>
<option value="MOR">Morelos</option>
<option value="NAY">Nayarit</option>
<option value="NLE">Nuevo León</option>
<option value="OAX">Oaxaca</option>
<option value="PUE">Puebla</option>
<option value="QUE">Querétaro</option>
<option value="ROO">Quintana Roo</option>
<option value="SIN">Sinaloa</option>
<option value="SLP">San Luis Potosí</option>
<option value="SON">Sonora</option>
<option value="TAB">Tabasco</option>
<option value="TAM">Tamaulipas</option>
<option value="TLA">Tlaxcala</option>
<option value="VER">Veracruz</option>
<option value="YUC">Yucatán</option>
<option value="ZAC">Zacatecas</option>
</select>"""
        self.assertEqual(str(self.form['state']), state_select_html)
