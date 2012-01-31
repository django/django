from django.contrib.localflavor.cl.forms import CLRutField, CLRegionSelect

from django.test import SimpleTestCase


class CLLocalFlavorTests(SimpleTestCase):
    def test_CLRegionSelect(self):
        f = CLRegionSelect()
        out = u'''<select name="foo">
<option value="RM">Regi\xf3n Metropolitana de Santiago</option>
<option value="I">Regi\xf3n de Tarapac\xe1</option>
<option value="II">Regi\xf3n de Antofagasta</option>
<option value="III">Regi\xf3n de Atacama</option>
<option value="IV">Regi\xf3n de Coquimbo</option>
<option value="V">Regi\xf3n de Valpara\xedso</option>
<option value="VI">Regi\xf3n del Libertador Bernardo O&#39;Higgins</option>
<option value="VII">Regi\xf3n del Maule</option>
<option value="VIII">Regi\xf3n del B\xedo B\xedo</option>
<option value="IX">Regi\xf3n de la Araucan\xeda</option>
<option value="X">Regi\xf3n de los Lagos</option>
<option value="XI">Regi\xf3n de Ays\xe9n del General Carlos Ib\xe1\xf1ez del Campo</option>
<option value="XII">Regi\xf3n de Magallanes y la Ant\xe1rtica Chilena</option>
<option value="XIV">Regi\xf3n de Los R\xedos</option>
<option value="XV">Regi\xf3n de Arica-Parinacota</option>
</select>'''
        self.assertHTMLEqual(f.render('foo', 'bar'), out)

    def test_CLRutField(self):
        error_invalid =  [u'The Chilean RUT is not valid.']
        error_format = [u'Enter a valid Chilean RUT. The format is XX.XXX.XXX-X.']
        valid = {
            '11-6': '11-6',
            '116': '11-6',
            '767484100': '76.748.410-0',
            '78.412.790-7': '78.412.790-7',
            '8.334.6043': '8.334.604-3',
            '76793310-K': '76.793.310-K',
            '76793310-k': '76.793.310-K',
        }
        invalid = {
            '11.111.111-0': error_invalid,
            '111': error_invalid,
        }
        self.assertFieldOutput(CLRutField, valid, invalid)

        # deal with special "Strict Mode".
        invalid = {
            '11-6': error_format,
            '767484100': error_format,
            '8.334.6043': error_format,
            '76793310-K': error_format,
            '11.111.111-0': error_invalid
        }
        self.assertFieldOutput(CLRutField,
            {}, invalid, field_kwargs={"strict": True}
        )
