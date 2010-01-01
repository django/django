# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ KW form fields.

tests = r"""
# KWCivilIDNumberField ########################################################

>>> from django.contrib.localflavor.kw.forms import KWCivilIDNumberField
>>> f = KWCivilIDNumberField()
>>> f.clean('282040701483')
'282040701483'
>>> f.clean('289332013455')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Kuwaiti Civil ID number']
"""
