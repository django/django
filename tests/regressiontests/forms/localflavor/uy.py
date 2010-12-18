from django.contrib.localflavor.uy.forms import UYDepartamentSelect, UYCIField
from django.contrib.localflavor.uy.util import get_validation_digit

from utils import LocalFlavorTestCase


class UYLocalFlavorTests(LocalFlavorTestCase):
    def test_UYDepartmentSelect(self):
        f = UYDepartamentSelect()
        out = u'''<select name="departamentos">
<option value="G">Artigas</option>
<option value="A">Canelones</option>
<option value="E">Cerro Largo</option>
<option value="L">Colonia</option>
<option value="Q">Durazno</option>
<option value="N">Flores</option>
<option value="O">Florida</option>
<option value="P">Lavalleja</option>
<option value="B">Maldonado</option>
<option value="S" selected="selected">Montevideo</option>
<option value="I">Paysand\xfa</option>
<option value="J">R\xedo Negro</option>
<option value="F">Rivera</option>
<option value="C">Rocha</option>
<option value="H">Salto</option>
<option value="M">San Jos\xe9</option>
<option value="K">Soriano</option>
<option value="R">Tacuaremb\xf3</option>
<option value="D">Treinta y Tres</option>
</select>'''
        self.assertEqual(f.render('departamentos', 'S'), out)
    
    def test_UYCIField(self):
        error_format = [u'Enter a valid CI number in X.XXX.XXX-X,XXXXXXX-X or XXXXXXXX format.']
        error_invalid = [u'Enter a valid CI number.']
        valid = {
            '4098053': '4098053',
            '409805-3': '409805-3',
            '409.805-3': '409.805-3',
            '10054112': '10054112',
            '1005411-2': '1005411-2',
            '1.005.411-2': '1.005.411-2',
        }
        invalid = {
            'foo': [u'Enter a valid CI number in X.XXX.XXX-X,XXXXXXX-X or XXXXXXXX format.'],
            '409805-2': [u'Enter a valid CI number.'],
            '1.005.411-5': [u'Enter a valid CI number.'],
        }
        self.assertFieldOutput(UYCIField, valid, invalid)
        self.assertEqual(get_validation_digit(409805), 3)
        self.assertEqual(get_validation_digit(1005411), 2)

