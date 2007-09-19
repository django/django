# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ DE form fields.

tests = r"""
# DEZipCodeField ##############################################################

>>> from django.contrib.localflavor.de.forms import DEZipCodeField
>>> f = DEZipCodeField()
>>> f.clean('99423')
u'99423'
>>> f.clean(' 99423')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']

# DEStateSelect #############################################################

>>> from django.contrib.localflavor.de.forms import DEStateSelect
>>> w = DEStateSelect()
>>> w.render('states', 'TH')
u'<select name="states">\n<option value="BW">Baden-Wuerttemberg</option>\n<option value="BY">Bavaria</option>\n<option value="BE">Berlin</option>\n<option value="BB">Brandenburg</option>\n<option value="HB">Bremen</option>\n<option value="HH">Hamburg</option>\n<option value="HE">Hessen</option>\n<option value="MV">Mecklenburg-Western Pomerania</option>\n<option value="NI">Lower Saxony</option>\n<option value="NW">North Rhine-Westphalia</option>\n<option value="RP">Rhineland-Palatinate</option>\n<option value="SL">Saarland</option>\n<option value="SN">Saxony</option>\n<option value="ST">Saxony-Anhalt</option>\n<option value="SH">Schleswig-Holstein</option>\n<option value="TH" selected="selected">Thuringia</option>\n</select>'

# DEIdentityCardNumberField #################################################

>>> from django.contrib.localflavor.de.forms import DEIdentityCardNumberField
>>> f = DEIdentityCardNumberField()
>>> f.clean('7549313035D-6004103-0903042-0')
u'7549313035D-6004103-0903042-0'
>>> f.clean('9786324830D 6104243 0910271 2')
u'9786324830D-6104243-0910271-2'
>>> f.clean('0434657485D-6407276-0508137-9')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid German identity card number in XXXXXXXXXXX-XXXXXXX-XXXXXXX-X format.']
"""
