# -*- coding: utf-8 -*-
# Tests to prevent against recurrences of earlier bugs.

regression_tests = r"""
It should be possible to re-use attribute dictionaries (#3810)
>>> from django.newforms import *
>>> extra_attrs = {'class': 'special'}
>>> class TestForm(Form):
...     f1 = CharField(max_length=10, widget=TextInput(attrs=extra_attrs))
...     f2 = CharField(widget=TextInput(attrs=extra_attrs))
>>> TestForm(auto_id=False).as_p()
u'<p>F1: <input type="text" class="special" name="f1" maxlength="10" /></p>\n<p>F2: <input type="text" class="special" name="f2" /></p>'
"""
