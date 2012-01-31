from django.contrib.localflavor.co.forms import CODepartmentSelect

from django.test import SimpleTestCase

class COLocalFlavorTests(SimpleTestCase):
    def test_CODepartmentSelect(self):
        d = CODepartmentSelect()
        out = u"""<select name="department">
<option value="AMA">Amazonas</option>
<option value="ANT">Antioquia</option>
<option value="ARA">Arauca</option>
<option value="ATL">Atl\xe1ntico</option>
<option value="DC">Bogot\xe1</option>
<option value="BOL">Bol\xedvar</option>
<option value="BOY">Boyac\xe1</option>
<option value="CAL">Caldas</option>
<option value="CAQ">Caquet\xe1</option>
<option value="CAS">Casanare</option>
<option value="CAU">Cauca</option>
<option value="CES">Cesar</option>
<option value="CHO">Choc\xf3</option>
<option value="COR" selected="selected">C\xf3rdoba</option>
<option value="CUN">Cundinamarca</option>
<option value="GUA">Guain\xeda</option>
<option value="GUV">Guaviare</option>
<option value="HUI">Huila</option>
<option value="LAG">La Guajira</option>
<option value="MAG">Magdalena</option>
<option value="MET">Meta</option>
<option value="NAR">Nari\xf1o</option>
<option value="NSA">Norte de Santander</option>
<option value="PUT">Putumayo</option>
<option value="QUI">Quind\xedo</option>
<option value="RIS">Risaralda</option>
<option value="SAP">San Andr\xe9s and Providencia</option>
<option value="SAN">Santander</option>
<option value="SUC">Sucre</option>
<option value="TOL">Tolima</option>
<option value="VAC">Valle del Cauca</option>
<option value="VAU">Vaup\xe9s</option>
<option value="VID">Vichada</option>
</select>"""
        self.assertHTMLEqual(d.render('department', 'COR'), out)
