# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ UY form fields.

tests = r"""
# UYDepartamentSelect #########################################################

>>> from django.contrib.localflavor.uy.forms import UYDepartamentSelect
>>> f = UYDepartamentSelect()
>>> f.render('departamentos', 'S')
u'<select name="departamentos">\n<option value="G">Artigas</option>\n<option value="A">Canelones</option>\n<option value="E">Cerro Largo</option>\n<option value="L">Colonia</option>\n<option value="Q">Durazno</option>\n<option value="N">Flores</option>\n<option value="O">Florida</option>\n<option value="P">Lavalleja</option>\n<option value="B">Maldonado</option>\n<option value="S" selected="selected">Montevideo</option>\n<option value="I">Paysand\xfa</option>\n<option value="J">R\xedo Negro</option>\n<option value="F">Rivera</option>\n<option value="C">Rocha</option>\n<option value="H">Salto</option>\n<option value="M">San Jos\xe9</option>\n<option value="K">Soriano</option>\n<option value="R">Tacuaremb\xf3</option>\n<option value="D">Treinta y Tres</option>\n</select>'

# UYCIField ###################################################################

>>> from django.contrib.localflavor.uy.util import get_validation_digit
>>> get_validation_digit(409805) == 3
True
>>> get_validation_digit(1005411) == 2
True

>>> from django.contrib.localflavor.uy.forms import UYCIField
>>> f = UYCIField()
>>> f.clean('4098053')
u'4098053'
>>> f.clean('409805-3')
u'409805-3'
>>> f.clean('409.805-3')
u'409.805-3'
>>> f.clean('10054112')
u'10054112'
>>> f.clean('1005411-2')
u'1005411-2'
>>> f.clean('1.005.411-2')
u'1.005.411-2'
>>> f.clean('foo')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CI number in X.XXX.XXX-X,XXXXXXX-X or XXXXXXXX format.']
>>> f.clean('409805-2')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CI number.']
>>> f.clean('1.005.411-5')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CI number.']
"""
