# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ IT form fields.

tests = r"""
# ITZipCodeField #############################################################

>>> from django.contrib.localflavor.it.forms import ITZipCodeField
>>> f = ITZipCodeField()
>>> f.clean('00100')
u'00100'
>>> f.clean(' 00100')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid zip code.']

# ITRegionSelect #############################################################

>>> from django.contrib.localflavor.it.forms import ITRegionSelect
>>> w = ITRegionSelect()
>>> w.render('regions', 'PMN')
u'<select name="regions">\n<option value="ABR">Abruzzo</option>\n<option value="BAS">Basilicata</option>\n<option value="CAL">Calabria</option>\n<option value="CAM">Campania</option>\n<option value="EMR">Emilia-Romagna</option>\n<option value="FVG">Friuli-Venezia Giulia</option>\n<option value="LAZ">Lazio</option>\n<option value="LIG">Liguria</option>\n<option value="LOM">Lombardia</option>\n<option value="MAR">Marche</option>\n<option value="MOL">Molise</option>\n<option value="PMN" selected="selected">Piemonte</option>\n<option value="PUG">Puglia</option>\n<option value="SAR">Sardegna</option>\n<option value="SIC">Sicilia</option>\n<option value="TOS">Toscana</option>\n<option value="TAA">Trentino-Alto Adige</option>\n<option value="UMB">Umbria</option>\n<option value="VAO">Valle d\u2019Aosta</option>\n<option value="VEN">Veneto</option>\n</select>'

# ITSocialSecurityNumberField #################################################

>>> from django.contrib.localflavor.it.forms import ITSocialSecurityNumberField
>>> f = ITSocialSecurityNumberField()
>>> f.clean('LVSGDU99T71H501L')
u'LVSGDU99T71H501L'
>>> f.clean('LBRRME11A01L736W')
u'LBRRME11A01L736W'
>>> f.clean('lbrrme11a01l736w')
u'LBRRME11A01L736W'
>>> f.clean('LBR RME 11A01 L736W')
u'LBRRME11A01L736W'
>>> f.clean('LBRRME11A01L736A')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Social Security number.']
>>> f.clean('%BRRME11A01L736W')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Social Security number.']

# ITVatNumberField ###########################################################

>>> from django.contrib.localflavor.it.forms import ITVatNumberField
>>> f = ITVatNumberField()
>>> f.clean('07973780013')
u'07973780013'
>>> f.clean('7973780013')
u'07973780013'
>>> f.clean(7973780013)
u'07973780013'
>>> f.clean('07973780014')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid VAT number.']
>>> f.clean('A7973780013')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid VAT number.']
"""
