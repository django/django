from django.contrib.localflavor.ec.forms import ECProvinceSelect

from django.test import SimpleTestCase

class ECLocalFlavorTests(SimpleTestCase):
    def test_ECProvinceSelect(self):
        p = ECProvinceSelect()
        out = u"""<select name="province">
<option value="A">Azuay</option>
<option value="B">Bol\xedvar</option>
<option value="F">Ca\xf1ar</option>
<option value="C">Carchi</option>
<option value="H">Chimborazo</option>
<option value="X">Cotopaxi</option>
<option value="O">El Oro</option>
<option value="E">Esmeraldas</option>
<option value="W">Gal\xe1pagos</option>
<option value="G">Guayas</option>
<option value="I">Imbabura</option>
<option value="L">Loja</option>
<option value="R">Los R\xedos</option>
<option value="M">Manab\xed</option>
<option value="S">Morona Santiago</option>
<option value="N">Napo</option>
<option value="D">Orellana</option>
<option value="Y">Pastaza</option>
<option value="P">Pichincha</option>
<option value="SE">Santa Elena</option>
<option value="SD">Santo Domingo de los Ts\xe1chilas</option>
<option value="U" selected="selected">Sucumb\xedos</option>
<option value="T">Tungurahua</option>
<option value="Z">Zamora Chinchipe</option>
</select>"""
        self.assertHTMLEqual(p.render('province', 'U'), out)
