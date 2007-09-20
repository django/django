# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ CH form fields.

tests = r"""
# CHZipCodeField ############################################################

>>> from django.contrib.localflavor.ch.forms import CHZipCodeField
>>> f = CHZipCodeField()
>>> f.clean('800x')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXX.']
>>> f.clean('80 00')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXX.']
>>> f.clean('8000')
u'8000'

# CHPhoneNumberField ########################################################

>>> from django.contrib.localflavor.ch.forms import CHPhoneNumberField
>>> f = CHPhoneNumberField()
>>> f.clean('01234567890')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in 0XX XXX XX XX format.']
>>> f.clean('1234567890')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in 0XX XXX XX XX format.']
>>> f.clean('0123456789')
u'012 345 67 89'

# CHIdentityCardNumberField #################################################

>>> from django.contrib.localflavor.ch.forms import CHIdentityCardNumberField
>>> f = CHIdentityCardNumberField()
>>> f.clean('C1234567<0')
u'C1234567<0'
>>> f.clean('C1234567<1')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swiss identity or passport card number in X1234567<0 or 1234567890 format.']
>>> f.clean('2123456700')
u'2123456700'
>>> f.clean('2123456701')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swiss identity or passport card number in X1234567<0 or 1234567890 format.']

# CHStateSelect #############################################################

>>> from django.contrib.localflavor.ch.forms import CHStateSelect
>>> w = CHStateSelect()
>>> w.render('state', 'AG')
u'<select name="state">\n<option value="AG" selected="selected">Aargau</option>\n<option value="AI">Appenzell Innerrhoden</option>\n<option value="AR">Appenzell Ausserrhoden</option>\n<option value="BS">Basel-Stadt</option>\n<option value="BL">Basel-Land</option>\n<option value="BE">Berne</option>\n<option value="FR">Fribourg</option>\n<option value="GE">Geneva</option>\n<option value="GL">Glarus</option>\n<option value="GR">Graubuenden</option>\n<option value="JU">Jura</option>\n<option value="LU">Lucerne</option>\n<option value="NE">Neuchatel</option>\n<option value="NW">Nidwalden</option>\n<option value="OW">Obwalden</option>\n<option value="SH">Schaffhausen</option>\n<option value="SZ">Schwyz</option>\n<option value="SO">Solothurn</option>\n<option value="SG">St. Gallen</option>\n<option value="TG">Thurgau</option>\n<option value="TI">Ticino</option>\n<option value="UR">Uri</option>\n<option value="VS">Valais</option>\n<option value="VD">Vaud</option>\n<option value="ZG">Zug</option>\n<option value="ZH">Zurich</option>\n</select>'
"""
