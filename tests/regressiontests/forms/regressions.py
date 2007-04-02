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

####################### 
# Tests for form i18n # 
####################### 
There were some problems with form translations in #3600
 
>>> from django.utils.translation import gettext_lazy, activate, deactivate
>>> class SomeForm(Form):
...     username = CharField(max_length=10, label=gettext_lazy('Username'))
>>> f = SomeForm()
>>> print f.as_p()
<p><label for="id_username">Username:</label> <input id="id_username" type="text" name="username" maxlength="10" /></p>
>>> activate('de')
>>> print f.as_p()
<p><label for="id_username">Benutzername:</label> <input id="id_username" type="text" name="username" maxlength="10" /></p>
>>> deactivate()
"""
