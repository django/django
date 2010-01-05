# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ AR form fields.

tests = r"""
# ARProvinceField #############################################################

>>> from django.contrib.localflavor.ar.forms import ARProvinceSelect
>>> f = ARProvinceSelect()
>>> f.render('provincias', 'A')
u'<select name="provincias">\n<option value="B">Buenos Aires</option>\n<option value="K">Catamarca</option>\n<option value="H">Chaco</option>\n<option value="U">Chubut</option>\n<option value="C">Ciudad Aut\xf3noma de Buenos Aires</option>\n<option value="X">C\xf3rdoba</option>\n<option value="W">Corrientes</option>\n<option value="E">Entre R\xedos</option>\n<option value="P">Formosa</option>\n<option value="Y">Jujuy</option>\n<option value="L">La Pampa</option>\n<option value="F">La Rioja</option>\n<option value="M">Mendoza</option>\n<option value="N">Misiones</option>\n<option value="Q">Neuqu\xe9n</option>\n<option value="R">R\xedo Negro</option>\n<option value="A" selected="selected">Salta</option>\n<option value="J">San Juan</option>\n<option value="D">San Luis</option>\n<option value="Z">Santa Cruz</option>\n<option value="S">Santa Fe</option>\n<option value="G">Santiago del Estero</option>\n<option value="V">Tierra del Fuego, Ant\xe1rtida e Islas del Atl\xe1ntico Sur</option>\n<option value="T">Tucum\xe1n</option>\n</select>'

# ARPostalCodeField ###########################################################

>>> from django.contrib.localflavor.ar.forms import ARPostalCodeField
>>> f = ARPostalCodeField()
>>> f.clean('5000')
u'5000'
>>> f.clean('C1064AAB')
u'C1064AAB'
>>> f.clean('c1064AAB')
u'C1064AAB'
>>> f.clean('C1064aab')
u'C1064AAB'
>>> f.clean(u'4400')
u'4400'
>>> f.clean(u'C1064AAB')
u'C1064AAB'
>>> f.clean('C1064AABB')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 8 characters (it has 9).', u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('C1064AA')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('C106AAB')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('106AAB')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('500')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 4 characters (it has 3).', u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('5PPP')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(u'')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = ARPostalCodeField(required=False)
>>> f.clean('5000')
u'5000'
>>> f.clean('C1064AAB')
u'C1064AAB'
>>> f.clean('c1064AAB')
u'C1064AAB'
>>> f.clean('C1064aab')
u'C1064AAB'
>>> f.clean(u'4400')
u'4400'
>>> f.clean(u'C1064AAB')
u'C1064AAB'
>>> f.clean('C1064AABB')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 8 characters (it has 9).', u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('C1064AA')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('C106AAB')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('106AAB')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('500')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 4 characters (it has 3).', u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean('5PPP')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format NNNN or ANNNNAAA.']
>>> f.clean(None)
u''
>>> f.clean('')
u''
>>> f.clean(u'')
u''

# ARDNIField ##################################################################

>>> from django.contrib.localflavor.ar.forms import ARDNIField
>>> f = ARDNIField()
>>> f.clean('20123456')
u'20123456'
>>> f.clean('20.123.456')
u'20123456'
>>> f.clean('9123456')
u'9123456'
>>> f.clean('9.123.456')
u'9123456'
>>> f.clean(u'20123456')
u'20123456'
>>> f.clean(u'20.123.456')
u'20123456'
>>> f.clean('20.123456')
u'20123456'
>>> f.clean('101234566')
Traceback (most recent call last):
...
ValidationError: [u'This field requires 7 or 8 digits.']
>>> f.clean('W0123456')
Traceback (most recent call last):
...
ValidationError: [u'This field requires only numbers.']
>>> f.clean('10,123,456')
Traceback (most recent call last):
...
ValidationError: [u'This field requires only numbers.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(u'')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = ARDNIField(required=False)
>>> f.clean('20123456')
u'20123456'
>>> f.clean('20.123.456')
u'20123456'
>>> f.clean('9123456')
u'9123456'
>>> f.clean('9.123.456')
u'9123456'
>>> f.clean(u'20123456')
u'20123456'
>>> f.clean(u'20.123.456')
u'20123456'
>>> f.clean('20.123456')
u'20123456'
>>> f.clean('101234566')
Traceback (most recent call last):
...
ValidationError: [u'This field requires 7 or 8 digits.']
>>> f.clean('W0123456')
Traceback (most recent call last):
...
ValidationError: [u'This field requires only numbers.']
>>> f.clean('10,123,456')
Traceback (most recent call last):
...
ValidationError: [u'This field requires only numbers.']
>>> f.clean(None)
u''
>>> f.clean('')
u''
>>> f.clean(u'')
u''

# ARCUITField #################################################################

>>> from django.contrib.localflavor.ar.forms import ARCUITField
>>> f = ARCUITField()
>>> f.clean('20-10123456-9')
u'20-10123456-9'
>>> f.clean(u'20-10123456-9')
u'20-10123456-9'
>>> f.clean('27-10345678-4')
u'27-10345678-4'
>>> f.clean('20101234569')
u'20-10123456-9'
>>> f.clean('27103456784')
u'27-10345678-4'
>>> f.clean('2-10123456-9')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('210123456-9')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('20-10123456')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('20-10123456-')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('20-10123456-5')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CUIT.']
>>> f.clean(u'2-10123456-9')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('27-10345678-1')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CUIT.']
>>> f.clean(u'27-10345678-1')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CUIT.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(u'')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = ARCUITField(required=False)
>>> f.clean('20-10123456-9')
u'20-10123456-9'
>>> f.clean(u'20-10123456-9')
u'20-10123456-9'
>>> f.clean('27-10345678-4')
u'27-10345678-4'
>>> f.clean('20101234569')
u'20-10123456-9'
>>> f.clean('27103456784')
u'27-10345678-4'
>>> f.clean('2-10123456-9')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('210123456-9')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('20-10123456')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('20-10123456-')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('20-10123456-5')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CUIT.']
>>> f.clean(u'2-10123456-9')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.']
>>> f.clean('27-10345678-1')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CUIT.']
>>> f.clean(u'27-10345678-1')
Traceback (most recent call last):
...
ValidationError: [u'Invalid CUIT.']
>>> f.clean(None)
u''
>>> f.clean('')
u''
>>> f.clean(u'')
u''
"""
