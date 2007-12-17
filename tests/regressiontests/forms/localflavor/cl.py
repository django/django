
# Tests for the contrib/localflavor/ CL form fields.

tests = r"""
## CLRutField #############################################################

CLRutField is a Field that checks the validity of the Chilean
personal identification number (RUT). It has two modes relaxed (default) and
strict.

>>> from django.contrib.localflavor.cl.forms import CLRutField
>>> rut = CLRutField()

>>> rut.clean('11-6')
u'11-6'
>>> rut.clean('116')
u'11-6'

# valid format, bad verifier.
>>> rut.clean('11.111.111-0')
Traceback (most recent call last):
...
ValidationError: [u'The Chilean RUT is not valid.']
>>> rut.clean('111')
Traceback (most recent call last):
...
ValidationError: [u'The Chilean RUT is not valid.']

>>> rut.clean('767484100')
u'76.748.410-0'
>>> rut.clean('78.412.790-7')
u'78.412.790-7'
>>> rut.clean('8.334.6043')
u'8.334.604-3'
>>> rut.clean('76793310-K')
u'76.793.310-K'

Strict RUT usage (does not allow imposible values)
>>> rut = CLRutField(strict=True)

>>> rut.clean('11-6')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Chilean RUT. The format is XX.XXX.XXX-X.']

# valid format, bad verifier.
>>> rut.clean('11.111.111-0')
Traceback (most recent call last):
...
ValidationError: [u'The Chilean RUT is not valid.']

# Correct input, invalid format.
>>> rut.clean('767484100')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Chilean RUT. The format is XX.XXX.XXX-X.']
>>> rut.clean('78.412.790-7')
u'78.412.790-7'
>>> rut.clean('8.334.6043')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Chilean RUT. The format is XX.XXX.XXX-X.']
>>> rut.clean('76793310-K')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Chilean RUT. The format is XX.XXX.XXX-X.']

## CLRegionSelect #########################################################
>>> from django.contrib.localflavor.cl.forms import CLRegionSelect
>>> f = CLRegionSelect()

>>> f.render('foo', 'bar')
u'<select name="foo">\n<option value="RM">Regi\xf3n Metropolitana de Santiago</option>\n<option value="I">Regi\xf3n de Tarapac\xe1</option>\n<option value="II">Regi\xf3n de Antofagasta</option>\n<option value="III">Regi\xf3n de Atacama</option>\n<option value="IV">Regi\xf3n de Coquimbo</option>\n<option value="V">Regi\xf3n de Valpara\xedso</option>\n<option value="VI">Regi\xf3n del Libertador Bernardo O&#39;Higgins</option>\n<option value="VII">Regi\xf3n del Maule</option>\n<option value="VIII">Regi\xf3n del B\xedo B\xedo</option>\n<option value="IX">Regi\xf3n de la Araucan\xeda</option>\n<option value="X">Regi\xf3n de los Lagos</option>\n<option value="XI">Regi\xf3n de Ays\xe9n del General Carlos Ib\xe1\xf1ez del Campo</option>\n<option value="XII">Regi\xf3n de Magallanes y la Ant\xe1rtica Chilena</option>\n<option value="XIV">Regi\xf3n de Los R\xedos</option>\n<option value="XV">Regi\xf3n de Arica-Parinacota</option>\n</select>'
"""
