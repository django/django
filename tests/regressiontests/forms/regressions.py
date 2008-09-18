# -*- coding: utf-8 -*-
# Tests to prevent against recurrences of earlier bugs.

tests = r"""
It should be possible to re-use attribute dictionaries (#3810)
>>> from django.forms import *
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

>>> from django.utils.translation import ugettext_lazy, activate, deactivate
>>> class SomeForm(Form):
...     username = CharField(max_length=10, label=ugettext_lazy('Username'))
>>> f = SomeForm()
>>> print f.as_p()
<p><label for="id_username">Username:</label> <input id="id_username" type="text" name="username" maxlength="10" /></p>

Translations are done at rendering time, so multi-lingual apps can define forms
early and still send back the right translation.

>>> activate('de')
>>> print f.as_p()
<p><label for="id_username">Benutzername:</label> <input id="id_username" type="text" name="username" maxlength="10" /></p>
>>> activate('pl')
>>> f.as_p()
u'<p><label for="id_username">Nazwa u\u017cytkownika:</label> <input id="id_username" type="text" name="username" maxlength="10" /></p>'
>>> deactivate()

There was some problems with form translations in #5216
>>> class SomeForm(Form):
...     field_1 = CharField(max_length=10, label=ugettext_lazy('field_1'))
...     field_2 = CharField(max_length=10, label=ugettext_lazy('field_2'), widget=TextInput(attrs={'id': 'field_2_id'}))
>>> f = SomeForm()
>>> print f['field_1'].label_tag()
<label for="id_field_1">field_1</label>
>>> print f['field_2'].label_tag()
<label for="field_2_id">field_2</label>

Unicode decoding problems...
>>> GENDERS = ((u'\xc5', u'En tied\xe4'), (u'\xf8', u'Mies'), (u'\xdf', u'Nainen'))
>>> class SomeForm(Form):
...     somechoice = ChoiceField(choices=GENDERS, widget=RadioSelect(), label=u'\xc5\xf8\xdf')
>>> f = SomeForm()
>>> f.as_p()
u'<p><label for="id_somechoice_0">\xc5\xf8\xdf:</label> <ul>\n<li><label for="id_somechoice_0"><input type="radio" id="id_somechoice_0" value="\xc5" name="somechoice" /> En tied\xe4</label></li>\n<li><label for="id_somechoice_1"><input type="radio" id="id_somechoice_1" value="\xf8" name="somechoice" /> Mies</label></li>\n<li><label for="id_somechoice_2"><input type="radio" id="id_somechoice_2" value="\xdf" name="somechoice" /> Nainen</label></li>\n</ul></p>'

Testing choice validation with UTF-8 bytestrings as input (these are the
Russian abbreviations "мес." and "шт.".

>>> UNITS = (('\xd0\xbc\xd0\xb5\xd1\x81.', '\xd0\xbc\xd0\xb5\xd1\x81.'), ('\xd1\x88\xd1\x82.', '\xd1\x88\xd1\x82.'))
>>> f = ChoiceField(choices=UNITS)
>>> f.clean(u'\u0448\u0442.')
u'\u0448\u0442.'
>>> f.clean('\xd1\x88\xd1\x82.')
u'\u0448\u0442.'

Translated error messages used to be buggy.
>>> activate('ru')
>>> f = SomeForm({})
>>> f.as_p()
u'<ul class="errorlist"><li>\u041e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u043e\u0435 \u043f\u043e\u043b\u0435.</li></ul>\n<p><label for="id_somechoice_0">\xc5\xf8\xdf:</label> <ul>\n<li><label for="id_somechoice_0"><input type="radio" id="id_somechoice_0" value="\xc5" name="somechoice" /> En tied\xe4</label></li>\n<li><label for="id_somechoice_1"><input type="radio" id="id_somechoice_1" value="\xf8" name="somechoice" /> Mies</label></li>\n<li><label for="id_somechoice_2"><input type="radio" id="id_somechoice_2" value="\xdf" name="somechoice" /> Nainen</label></li>\n</ul></p>'
>>> deactivate()

Deep copying translated text shouldn't raise an error
>>> from django.utils.translation import gettext_lazy
>>> class CopyForm(Form):
...     degree = IntegerField(widget=Select(choices=((1, gettext_lazy('test')),)))
>>> f = CopyForm()

#######################
# Miscellaneous Tests #
#######################

There once was a problem with Form fields called "data". Let's make sure that
doesn't come back.
>>> class DataForm(Form):
...     data = CharField(max_length=10)
>>> f = DataForm({'data': 'xyzzy'})
>>> f.is_valid()
True
>>> f.cleaned_data
{'data': u'xyzzy'}

A form with *only* hidden fields that has errors is going to be very unusual.
But we can try to make sure it doesn't generate invalid XHTML. In this case,
the as_p() method is the tricky one, since error lists cannot be nested
(validly) inside p elements.

>>> class HiddenForm(Form):
...     data = IntegerField(widget=HiddenInput)
>>> f = HiddenForm({})
>>> f.as_p()
u'<ul class="errorlist"><li>(Hidden field data) This field is required.</li></ul>\n<p> <input type="hidden" name="data" id="id_data" /></p>'
>>> f.as_table()
u'<tr><td colspan="2"><ul class="errorlist"><li>(Hidden field data) This field is required.</li></ul><input type="hidden" name="data" id="id_data" /></td></tr>'

"""
