from django.contrib.localflavor.py.forms import (PyDepartmentSelect,
    PyNumberedDepartmentSelect)

from django.test import SimpleTestCase

class PYLocalFlavorTests(SimpleTestCase):
    def test_PyDepartmentSelect(self):
        py = PyDepartmentSelect()
        out = u'''<select name="department">
<option value="AG">Alto Paraguay</option>
<option value="AA">Alto Paran\xe1</option>
<option value="AM">Amambay</option>
<option value="AS">Asunci\xf3n</option>
<option value="BQ">Boquer\xf3n</option>
<option value="CG">Caaguaz\xfa</option>
<option value="CZ">Caazap\xe1</option>
<option value="CY">Canindey\xfa</option>
<option value="CE">Central</option>
<option value="CN">Concepci\xf3n</option>
<option value="CR">Cordillera</option>
<option value="GU">Guair\xe1</option>
<option value="IT">Itap\xfaa</option>
<option value="MI">Misiones</option>
<option value="NE">\xd1eembuc\xfa</option>
<option value="PG">Paraguar\xed</option>
<option value="PH">Pdte. Hayes</option>
<option value="SP">San Pedro</option>
</select>'''
        self.assertHTMLEqual(py.render('department', 'M'), out)

    def test_PyNumberedDepartmentSelect(self):
        py = PyNumberedDepartmentSelect()
        out = u'''<select name="department">
<option value="CN">I Concepci\xf3n</option>
<option value="SP">II San Pedro</option>
<option value="CR">III Cordillera</option>
<option value="GU">IV Guair\xe1</option>
<option value="CG">V Caaguaz\xfa</option>
<option value="CZ">VI Caazap\xe1</option>
<option value="IT">VII Itap\xfaa</option>
<option value="MI">VIII Misiones</option>
<option value="PG">IX Paraguar\xed</option>
<option value="AA">X Alto Paran\xe1</option>
<option value="CE">XI Central</option>
<option value="NE">XII \xd1eembuc\xfa</option>
<option value="AM" selected="selected">XIII Amambay</option>
<option value="CY">XIV Canindey\xfa</option>
<option value="PH">XV Pdte. Hayes</option>
<option value="AG">XVI Alto Paraguay</option>
<option value="BQ">XVII Boquer\xf3n</option>
<option value="AS">XVIII Asunci\xf3n</option>
</select>'''
        self.assertHTMLEqual(py.render('department', 'AM'), out)
