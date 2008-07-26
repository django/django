# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ AT form fields.

tests = r"""
# ATZipCodeField ###########################################################

>>> from django.contrib.localflavor.at.forms import ATZipCodeField 
>>> f = ATZipCodeField()
>>> f.clean('1150')
u'1150'
>>> f.clean('4020')
u'4020'
>>> f.clean('8020')
u'8020'
>>> f.clean('111222')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXX.']
>>> f.clean('eeffee')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXX.']
>>> f.clean(u'')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']


>>> f = ATZipCodeField(required=False)
>>> f.clean('1150')
u'1150'
>>> f.clean('4020')
u'4020'
>>> f.clean('8020')
u'8020'
>>> f.clean('111222')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXX.']
>>> f.clean('eeffee')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXX.']
>>> f.clean(None)
u''
>>> f.clean('')
u''
>>> f.clean(u'')
u''

# ATStateSelect ##################################################################

>>> from django.contrib.localflavor.at.forms import ATStateSelect
>>> f = ATStateSelect()
>>> f.render('bundesland', 'WI')
u'<select name="bundesland">\n<option value="BL">Burgenland</option>\n<option value="KA">Carinthia</option>\n<option value="NO">Lower Austria</option>\n<option value="OO">Upper Austria</option>\n<option value="SA">Salzburg</option>\n<option value="ST">Styria</option>\n<option value="TI">Tyrol</option>\n<option value="VO">Vorarlberg</option>\n<option value="WI" selected="selected">Vienna</option>\n</select>'

"""
