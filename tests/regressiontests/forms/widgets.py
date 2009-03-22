# -*- coding: utf-8 -*-
tests = r"""
>>> from django.forms import *
>>> from django.forms.widgets import RadioFieldRenderer
>>> from django.utils.safestring import mark_safe
>>> import datetime
>>> import time
>>> import re
>>> try:
...     from decimal import Decimal
... except ImportError:
...     from django.utils._decimal import Decimal

###########
# Widgets #
###########

Each Widget class corresponds to an HTML form widget. A Widget knows how to
render itself, given a field name and some data. Widgets don't perform
validation.

# TextInput Widget ############################################################

>>> w = TextInput()
>>> w.render('email', '')
u'<input type="text" name="email" />'
>>> w.render('email', None)
u'<input type="text" name="email" />'
>>> w.render('email', 'test@example.com')
u'<input type="text" name="email" value="test@example.com" />'
>>> w.render('email', 'some "quoted" & ampersanded value')
u'<input type="text" name="email" value="some &quot;quoted&quot; &amp; ampersanded value" />'
>>> w.render('email', 'test@example.com', attrs={'class': 'fun'})
u'<input type="text" name="email" value="test@example.com" class="fun" />'

# Note that doctest in Python 2.4 (and maybe 2.5?) doesn't support non-ascii
# characters in output, so we're displaying the repr() here.
>>> w.render('email', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'})
u'<input type="text" name="email" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" class="fun" />'

You can also pass 'attrs' to the constructor:
>>> w = TextInput(attrs={'class': 'fun'})
>>> w.render('email', '')
u'<input type="text" class="fun" name="email" />'
>>> w.render('email', 'foo@example.com')
u'<input type="text" class="fun" value="foo@example.com" name="email" />'

'attrs' passed to render() get precedence over those passed to the constructor:
>>> w = TextInput(attrs={'class': 'pretty'})
>>> w.render('email', '', attrs={'class': 'special'})
u'<input type="text" class="special" name="email" />'

'attrs' can be safe-strings if needed
>>> w = TextInput(attrs={'onBlur': mark_safe("function('foo')")})
>>> print w.render('email', '')
<input onBlur="function('foo')" type="text" name="email" />

# PasswordInput Widget ############################################################

>>> w = PasswordInput()
>>> w.render('email', '')
u'<input type="password" name="email" />'
>>> w.render('email', None)
u'<input type="password" name="email" />'
>>> w.render('email', 'test@example.com')
u'<input type="password" name="email" value="test@example.com" />'
>>> w.render('email', 'some "quoted" & ampersanded value')
u'<input type="password" name="email" value="some &quot;quoted&quot; &amp; ampersanded value" />'
>>> w.render('email', 'test@example.com', attrs={'class': 'fun'})
u'<input type="password" name="email" value="test@example.com" class="fun" />'

You can also pass 'attrs' to the constructor:
>>> w = PasswordInput(attrs={'class': 'fun'})
>>> w.render('email', '')
u'<input type="password" class="fun" name="email" />'
>>> w.render('email', 'foo@example.com')
u'<input type="password" class="fun" value="foo@example.com" name="email" />'

'attrs' passed to render() get precedence over those passed to the constructor:
>>> w = PasswordInput(attrs={'class': 'pretty'})
>>> w.render('email', '', attrs={'class': 'special'})
u'<input type="password" class="special" name="email" />'

>>> w.render('email', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'})
u'<input type="password" class="fun" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" name="email" />'

The render_value argument lets you specify whether the widget should render
its value. You may want to do this for security reasons.
>>> w = PasswordInput(render_value=True)
>>> w.render('email', 'secret')
u'<input type="password" name="email" value="secret" />'
>>> w = PasswordInput(render_value=False)
>>> w.render('email', '')
u'<input type="password" name="email" />'
>>> w.render('email', None)
u'<input type="password" name="email" />'
>>> w.render('email', 'secret')
u'<input type="password" name="email" />'
>>> w = PasswordInput(attrs={'class': 'fun'}, render_value=False)
>>> w.render('email', 'secret')
u'<input type="password" class="fun" name="email" />'

# HiddenInput Widget ############################################################

>>> w = HiddenInput()
>>> w.render('email', '')
u'<input type="hidden" name="email" />'
>>> w.render('email', None)
u'<input type="hidden" name="email" />'
>>> w.render('email', 'test@example.com')
u'<input type="hidden" name="email" value="test@example.com" />'
>>> w.render('email', 'some "quoted" & ampersanded value')
u'<input type="hidden" name="email" value="some &quot;quoted&quot; &amp; ampersanded value" />'
>>> w.render('email', 'test@example.com', attrs={'class': 'fun'})
u'<input type="hidden" name="email" value="test@example.com" class="fun" />'

You can also pass 'attrs' to the constructor:
>>> w = HiddenInput(attrs={'class': 'fun'})
>>> w.render('email', '')
u'<input type="hidden" class="fun" name="email" />'
>>> w.render('email', 'foo@example.com')
u'<input type="hidden" class="fun" value="foo@example.com" name="email" />'

'attrs' passed to render() get precedence over those passed to the constructor:
>>> w = HiddenInput(attrs={'class': 'pretty'})
>>> w.render('email', '', attrs={'class': 'special'})
u'<input type="hidden" class="special" name="email" />'

>>> w.render('email', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'})
u'<input type="hidden" class="fun" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" name="email" />'

'attrs' passed to render() get precedence over those passed to the constructor:
>>> w = HiddenInput(attrs={'class': 'pretty'})
>>> w.render('email', '', attrs={'class': 'special'})
u'<input type="hidden" class="special" name="email" />'

Boolean values are rendered to their string forms ("True" and "False").
>>> w = HiddenInput()
>>> w.render('get_spam', False)
u'<input type="hidden" name="get_spam" value="False" />'
>>> w.render('get_spam', True)
u'<input type="hidden" name="get_spam" value="True" />'

# MultipleHiddenInput Widget ##################################################

>>> w = MultipleHiddenInput()
>>> w.render('email', [])
u''
>>> w.render('email', None)
u''
>>> w.render('email', ['test@example.com'])
u'<input type="hidden" name="email" value="test@example.com" />'
>>> w.render('email', ['some "quoted" & ampersanded value'])
u'<input type="hidden" name="email" value="some &quot;quoted&quot; &amp; ampersanded value" />'
>>> w.render('email', ['test@example.com', 'foo@example.com'])
u'<input type="hidden" name="email" value="test@example.com" />\n<input type="hidden" name="email" value="foo@example.com" />'
>>> w.render('email', ['test@example.com'], attrs={'class': 'fun'})
u'<input type="hidden" name="email" value="test@example.com" class="fun" />'
>>> w.render('email', ['test@example.com', 'foo@example.com'], attrs={'class': 'fun'})
u'<input type="hidden" name="email" value="test@example.com" class="fun" />\n<input type="hidden" name="email" value="foo@example.com" class="fun" />'

You can also pass 'attrs' to the constructor:
>>> w = MultipleHiddenInput(attrs={'class': 'fun'})
>>> w.render('email', [])
u''
>>> w.render('email', ['foo@example.com'])
u'<input type="hidden" class="fun" value="foo@example.com" name="email" />'
>>> w.render('email', ['foo@example.com', 'test@example.com'])
u'<input type="hidden" class="fun" value="foo@example.com" name="email" />\n<input type="hidden" class="fun" value="test@example.com" name="email" />'

'attrs' passed to render() get precedence over those passed to the constructor:
>>> w = MultipleHiddenInput(attrs={'class': 'pretty'})
>>> w.render('email', ['foo@example.com'], attrs={'class': 'special'})
u'<input type="hidden" class="special" value="foo@example.com" name="email" />'

>>> w.render('email', ['ŠĐĆŽćžšđ'], attrs={'class': 'fun'})
u'<input type="hidden" class="fun" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" name="email" />'

'attrs' passed to render() get precedence over those passed to the constructor:
>>> w = MultipleHiddenInput(attrs={'class': 'pretty'})
>>> w.render('email', ['foo@example.com'], attrs={'class': 'special'})
u'<input type="hidden" class="special" value="foo@example.com" name="email" />'

# FileInput Widget ############################################################

FileInput widgets don't ever show the value, because the old value is of no use
if you are updating the form or if the provided file generated an error.
>>> w = FileInput()
>>> w.render('email', '')
u'<input type="file" name="email" />'
>>> w.render('email', None)
u'<input type="file" name="email" />'
>>> w.render('email', 'test@example.com')
u'<input type="file" name="email" />'
>>> w.render('email', 'some "quoted" & ampersanded value')
u'<input type="file" name="email" />'
>>> w.render('email', 'test@example.com', attrs={'class': 'fun'})
u'<input type="file" name="email" class="fun" />'

You can also pass 'attrs' to the constructor:
>>> w = FileInput(attrs={'class': 'fun'})
>>> w.render('email', '')
u'<input type="file" class="fun" name="email" />'
>>> w.render('email', 'foo@example.com')
u'<input type="file" class="fun" name="email" />'

>>> w.render('email', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'})
u'<input type="file" class="fun" name="email" />'

Test for the behavior of _has_changed for FileInput. The value of data will
more than likely come from request.FILES. The value of initial data will
likely be a filename stored in the database. Since its value is of no use to
a FileInput it is ignored.

>>> w = FileInput()

# No file was uploaded and no initial data.
>>> w._has_changed(u'', None)
False

# A file was uploaded and no initial data.
>>> w._has_changed(u'', {'filename': 'resume.txt', 'content': 'My resume'})
True

# A file was not uploaded, but there is initial data
>>> w._has_changed(u'resume.txt', None)
False

# A file was uploaded and there is initial data (file identity is not dealt
# with here)
>>> w._has_changed('resume.txt', {'filename': 'resume.txt', 'content': 'My resume'})
True

# Textarea Widget #############################################################

>>> w = Textarea()
>>> w.render('msg', '')
u'<textarea rows="10" cols="40" name="msg"></textarea>'
>>> w.render('msg', None)
u'<textarea rows="10" cols="40" name="msg"></textarea>'
>>> w.render('msg', 'value')
u'<textarea rows="10" cols="40" name="msg">value</textarea>'
>>> w.render('msg', 'some "quoted" & ampersanded value')
u'<textarea rows="10" cols="40" name="msg">some &quot;quoted&quot; &amp; ampersanded value</textarea>'
>>> w.render('msg', mark_safe('pre &quot;quoted&quot; value'))
u'<textarea rows="10" cols="40" name="msg">pre &quot;quoted&quot; value</textarea>'
>>> w.render('msg', 'value', attrs={'class': 'pretty', 'rows': 20})
u'<textarea class="pretty" rows="20" cols="40" name="msg">value</textarea>'

You can also pass 'attrs' to the constructor:
>>> w = Textarea(attrs={'class': 'pretty'})
>>> w.render('msg', '')
u'<textarea rows="10" cols="40" name="msg" class="pretty"></textarea>'
>>> w.render('msg', 'example')
u'<textarea rows="10" cols="40" name="msg" class="pretty">example</textarea>'

'attrs' passed to render() get precedence over those passed to the constructor:
>>> w = Textarea(attrs={'class': 'pretty'})
>>> w.render('msg', '', attrs={'class': 'special'})
u'<textarea rows="10" cols="40" name="msg" class="special"></textarea>'

>>> w.render('msg', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'})
u'<textarea rows="10" cols="40" name="msg" class="fun">\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111</textarea>'

# CheckboxInput Widget ########################################################

>>> w = CheckboxInput()
>>> w.render('is_cool', '')
u'<input type="checkbox" name="is_cool" />'
>>> w.render('is_cool', None)
u'<input type="checkbox" name="is_cool" />'
>>> w.render('is_cool', False)
u'<input type="checkbox" name="is_cool" />'
>>> w.render('is_cool', True)
u'<input checked="checked" type="checkbox" name="is_cool" />'

Using any value that's not in ('', None, False, True) will check the checkbox
and set the 'value' attribute.
>>> w.render('is_cool', 'foo')
u'<input checked="checked" type="checkbox" name="is_cool" value="foo" />'

>>> w.render('is_cool', False, attrs={'class': 'pretty'})
u'<input type="checkbox" name="is_cool" class="pretty" />'

You can also pass 'attrs' to the constructor:
>>> w = CheckboxInput(attrs={'class': 'pretty'})
>>> w.render('is_cool', '')
u'<input type="checkbox" class="pretty" name="is_cool" />'

'attrs' passed to render() get precedence over those passed to the constructor:
>>> w = CheckboxInput(attrs={'class': 'pretty'})
>>> w.render('is_cool', '', attrs={'class': 'special'})
u'<input type="checkbox" class="special" name="is_cool" />'

You can pass 'check_test' to the constructor. This is a callable that takes the
value and returns True if the box should be checked.
>>> w = CheckboxInput(check_test=lambda value: value.startswith('hello'))
>>> w.render('greeting', '')
u'<input type="checkbox" name="greeting" />'
>>> w.render('greeting', 'hello')
u'<input checked="checked" type="checkbox" name="greeting" value="hello" />'
>>> w.render('greeting', 'hello there')
u'<input checked="checked" type="checkbox" name="greeting" value="hello there" />'
>>> w.render('greeting', 'hello & goodbye')
u'<input checked="checked" type="checkbox" name="greeting" value="hello &amp; goodbye" />'

A subtlety: If the 'check_test' argument cannot handle a value and raises any
exception during its __call__, then the exception will be swallowed and the box
will not be checked. In this example, the 'check_test' assumes the value has a
startswith() method, which fails for the values True, False and None.
>>> w.render('greeting', True)
u'<input type="checkbox" name="greeting" />'
>>> w.render('greeting', False)
u'<input type="checkbox" name="greeting" />'
>>> w.render('greeting', None)
u'<input type="checkbox" name="greeting" />'

The CheckboxInput widget will return False if the key is not found in the data
dictionary (because HTML form submission doesn't send any result for unchecked
checkboxes).
>>> w.value_from_datadict({}, {}, 'testing')
False

>>> w._has_changed(None, None)
False
>>> w._has_changed(None, u'')
False
>>> w._has_changed(u'', None)
False
>>> w._has_changed(u'', u'')
False
>>> w._has_changed(False, u'on')
True
>>> w._has_changed(True, u'on')
False
>>> w._has_changed(True, u'')
True

# Select Widget ###############################################################

>>> w = Select()
>>> print w.render('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<select name="beatle">
<option value="J" selected="selected">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>

If the value is None, none of the options are selected:
>>> print w.render('beatle', None, choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<select name="beatle">
<option value="J">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>

If the value corresponds to a label (but not to an option value), none of the options are selected:
>>> print w.render('beatle', 'John', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<select name="beatle">
<option value="J">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>

The value is compared to its str():
>>> print w.render('num', 2, choices=[('1', '1'), ('2', '2'), ('3', '3')])
<select name="num">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>
>>> print w.render('num', '2', choices=[(1, 1), (2, 2), (3, 3)])
<select name="num">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>
>>> print w.render('num', 2, choices=[(1, 1), (2, 2), (3, 3)])
<select name="num">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>

The 'choices' argument can be any iterable:
>>> from itertools import chain
>>> def get_choices():
...     for i in range(5):
...         yield (i, i)
>>> print w.render('num', 2, choices=get_choices())
<select name="num">
<option value="0">0</option>
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
<option value="4">4</option>
</select>
>>> things = ({'id': 1, 'name': 'And Boom'}, {'id': 2, 'name': 'One More Thing!'})
>>> class SomeForm(Form):
...     somechoice = ChoiceField(choices=chain((('', '-'*9),), [(thing['id'], thing['name']) for thing in things]))
>>> f = SomeForm()
>>> f.as_table()
u'<tr><th><label for="id_somechoice">Somechoice:</label></th><td><select name="somechoice" id="id_somechoice">\n<option value="" selected="selected">---------</option>\n<option value="1">And Boom</option>\n<option value="2">One More Thing!</option>\n</select></td></tr>'
>>> f.as_table()
u'<tr><th><label for="id_somechoice">Somechoice:</label></th><td><select name="somechoice" id="id_somechoice">\n<option value="" selected="selected">---------</option>\n<option value="1">And Boom</option>\n<option value="2">One More Thing!</option>\n</select></td></tr>'
>>> f = SomeForm({'somechoice': 2})
>>> f.as_table()
u'<tr><th><label for="id_somechoice">Somechoice:</label></th><td><select name="somechoice" id="id_somechoice">\n<option value="">---------</option>\n<option value="1">And Boom</option>\n<option value="2" selected="selected">One More Thing!</option>\n</select></td></tr>'

You can also pass 'choices' to the constructor:
>>> w = Select(choices=[(1, 1), (2, 2), (3, 3)])
>>> print w.render('num', 2)
<select name="num">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>

If 'choices' is passed to both the constructor and render(), then they'll both be in the output:
>>> print w.render('num', 2, choices=[(4, 4), (5, 5)])
<select name="num">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
<option value="4">4</option>
<option value="5">5</option>
</select>

# Choices are escaped correctly
>>> print w.render('escape', None, choices=(('bad', 'you & me'), ('good', mark_safe('you &gt; me'))))
<select name="escape">
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="bad">you &amp; me</option>
<option value="good">you &gt; me</option>
</select>

# Unicode choices are correctly rendered as HTML
>>> w.render('email', 'ŠĐĆŽćžšđ', choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')])
u'<select name="email">\n<option value="1">1</option>\n<option value="2">2</option>\n<option value="3">3</option>\n<option value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" selected="selected">\u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111</option>\n<option value="\u0107\u017e\u0161\u0111">abc\u0107\u017e\u0161\u0111</option>\n</select>'

If choices is passed to the constructor and is a generator, it can be iterated
over multiple times without getting consumed:
>>> w = Select(choices=get_choices())
>>> print w.render('num', 2)
<select name="num">
<option value="0">0</option>
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
<option value="4">4</option>
</select>
>>> print w.render('num', 3)
<select name="num">
<option value="0">0</option>
<option value="1">1</option>
<option value="2">2</option>
<option value="3" selected="selected">3</option>
<option value="4">4</option>
</select>

Choices can be nested one level in order to create HTML optgroups:
>>> w.choices=(('outer1', 'Outer 1'), ('Group "1"', (('inner1', 'Inner 1'), ('inner2', 'Inner 2'))))
>>> print w.render('nestchoice', None)
<select name="nestchoice">
<option value="outer1">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>

>>> print w.render('nestchoice', 'outer1')
<select name="nestchoice">
<option value="outer1" selected="selected">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>

>>> print w.render('nestchoice', 'inner1')
<select name="nestchoice">
<option value="outer1">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1" selected="selected">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>

# NullBooleanSelect Widget ####################################################

>>> w = NullBooleanSelect()
>>> print w.render('is_cool', True)
<select name="is_cool">
<option value="1">Unknown</option>
<option value="2" selected="selected">Yes</option>
<option value="3">No</option>
</select>
>>> print w.render('is_cool', False)
<select name="is_cool">
<option value="1">Unknown</option>
<option value="2">Yes</option>
<option value="3" selected="selected">No</option>
</select>
>>> print w.render('is_cool', None)
<select name="is_cool">
<option value="1" selected="selected">Unknown</option>
<option value="2">Yes</option>
<option value="3">No</option>
</select>
>>> print w.render('is_cool', '2')
<select name="is_cool">
<option value="1">Unknown</option>
<option value="2" selected="selected">Yes</option>
<option value="3">No</option>
</select>
>>> print w.render('is_cool', '3')
<select name="is_cool">
<option value="1">Unknown</option>
<option value="2">Yes</option>
<option value="3" selected="selected">No</option>
</select>

""" + \
r""" # [This concatenation is to keep the string below the jython's 32K limit].
# SelectMultiple Widget #######################################################

>>> w = SelectMultiple()
>>> print w.render('beatles', ['J'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<select multiple="multiple" name="beatles">
<option value="J" selected="selected">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>
>>> print w.render('beatles', ['J', 'P'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<select multiple="multiple" name="beatles">
<option value="J" selected="selected">John</option>
<option value="P" selected="selected">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>
>>> print w.render('beatles', ['J', 'P', 'R'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<select multiple="multiple" name="beatles">
<option value="J" selected="selected">John</option>
<option value="P" selected="selected">Paul</option>
<option value="G">George</option>
<option value="R" selected="selected">Ringo</option>
</select>

If the value is None, none of the options are selected:
>>> print w.render('beatles', None, choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<select multiple="multiple" name="beatles">
<option value="J">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>

If the value corresponds to a label (but not to an option value), none of the options are selected:
>>> print w.render('beatles', ['John'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<select multiple="multiple" name="beatles">
<option value="J">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>

If multiple values are given, but some of them are not valid, the valid ones are selected:
>>> print w.render('beatles', ['J', 'G', 'foo'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<select multiple="multiple" name="beatles">
<option value="J" selected="selected">John</option>
<option value="P">Paul</option>
<option value="G" selected="selected">George</option>
<option value="R">Ringo</option>
</select>

The value is compared to its str():
>>> print w.render('nums', [2], choices=[('1', '1'), ('2', '2'), ('3', '3')])
<select multiple="multiple" name="nums">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>
>>> print w.render('nums', ['2'], choices=[(1, 1), (2, 2), (3, 3)])
<select multiple="multiple" name="nums">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>
>>> print w.render('nums', [2], choices=[(1, 1), (2, 2), (3, 3)])
<select multiple="multiple" name="nums">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>

The 'choices' argument can be any iterable:
>>> def get_choices():
...     for i in range(5):
...         yield (i, i)
>>> print w.render('nums', [2], choices=get_choices())
<select multiple="multiple" name="nums">
<option value="0">0</option>
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
<option value="4">4</option>
</select>

You can also pass 'choices' to the constructor:
>>> w = SelectMultiple(choices=[(1, 1), (2, 2), (3, 3)])
>>> print w.render('nums', [2])
<select multiple="multiple" name="nums">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>

If 'choices' is passed to both the constructor and render(), then they'll both be in the output:
>>> print w.render('nums', [2], choices=[(4, 4), (5, 5)])
<select multiple="multiple" name="nums">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
<option value="4">4</option>
<option value="5">5</option>
</select>

# Choices are escaped correctly
>>> print w.render('escape', None, choices=(('bad', 'you & me'), ('good', mark_safe('you &gt; me'))))
<select multiple="multiple" name="escape">
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="bad">you &amp; me</option>
<option value="good">you &gt; me</option>
</select>

# Unicode choices are correctly rendered as HTML
>>> w.render('nums', ['ŠĐĆŽćžšđ'], choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')])
u'<select multiple="multiple" name="nums">\n<option value="1">1</option>\n<option value="2">2</option>\n<option value="3">3</option>\n<option value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" selected="selected">\u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111</option>\n<option value="\u0107\u017e\u0161\u0111">abc\u0107\u017e\u0161\u0111</option>\n</select>'

# Test the usage of _has_changed
>>> w._has_changed(None, None)
False
>>> w._has_changed([], None)
False
>>> w._has_changed(None, [u'1'])
True
>>> w._has_changed([1, 2], [u'1', u'2'])
False
>>> w._has_changed([1, 2], [u'1'])
True
>>> w._has_changed([1, 2], [u'1', u'3'])
True

# Choices can be nested one level in order to create HTML optgroups:
>>> w.choices = (('outer1', 'Outer 1'), ('Group "1"', (('inner1', 'Inner 1'), ('inner2', 'Inner 2'))))
>>> print w.render('nestchoice', None)
<select multiple="multiple" name="nestchoice">
<option value="outer1">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>

>>> print w.render('nestchoice', ['outer1'])
<select multiple="multiple" name="nestchoice">
<option value="outer1" selected="selected">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>

>>> print w.render('nestchoice', ['inner1'])
<select multiple="multiple" name="nestchoice">
<option value="outer1">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1" selected="selected">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>

>>> print w.render('nestchoice', ['outer1', 'inner2'])
<select multiple="multiple" name="nestchoice">
<option value="outer1" selected="selected">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1">Inner 1</option>
<option value="inner2" selected="selected">Inner 2</option>
</optgroup>
</select>

# RadioSelect Widget ##########################################################

>>> w = RadioSelect()
>>> print w.render('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label><input checked="checked" type="radio" name="beatle" value="J" /> John</label></li>
<li><label><input type="radio" name="beatle" value="P" /> Paul</label></li>
<li><label><input type="radio" name="beatle" value="G" /> George</label></li>
<li><label><input type="radio" name="beatle" value="R" /> Ringo</label></li>
</ul>

If the value is None, none of the options are checked:
>>> print w.render('beatle', None, choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label><input type="radio" name="beatle" value="J" /> John</label></li>
<li><label><input type="radio" name="beatle" value="P" /> Paul</label></li>
<li><label><input type="radio" name="beatle" value="G" /> George</label></li>
<li><label><input type="radio" name="beatle" value="R" /> Ringo</label></li>
</ul>

If the value corresponds to a label (but not to an option value), none of the options are checked:
>>> print w.render('beatle', 'John', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label><input type="radio" name="beatle" value="J" /> John</label></li>
<li><label><input type="radio" name="beatle" value="P" /> Paul</label></li>
<li><label><input type="radio" name="beatle" value="G" /> George</label></li>
<li><label><input type="radio" name="beatle" value="R" /> Ringo</label></li>
</ul>

The value is compared to its str():
>>> print w.render('num', 2, choices=[('1', '1'), ('2', '2'), ('3', '3')])
<ul>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
</ul>
>>> print w.render('num', '2', choices=[(1, 1), (2, 2), (3, 3)])
<ul>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
</ul>
>>> print w.render('num', 2, choices=[(1, 1), (2, 2), (3, 3)])
<ul>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
</ul>

The 'choices' argument can be any iterable:
>>> def get_choices():
...     for i in range(5):
...         yield (i, i)
>>> print w.render('num', 2, choices=get_choices())
<ul>
<li><label><input type="radio" name="num" value="0" /> 0</label></li>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
<li><label><input type="radio" name="num" value="4" /> 4</label></li>
</ul>

You can also pass 'choices' to the constructor:
>>> w = RadioSelect(choices=[(1, 1), (2, 2), (3, 3)])
>>> print w.render('num', 2)
<ul>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
</ul>

If 'choices' is passed to both the constructor and render(), then they'll both be in the output:
>>> print w.render('num', 2, choices=[(4, 4), (5, 5)])
<ul>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
<li><label><input type="radio" name="num" value="4" /> 4</label></li>
<li><label><input type="radio" name="num" value="5" /> 5</label></li>
</ul>

RadioSelect uses a RadioFieldRenderer to render the individual radio inputs.
You can manipulate that object directly to customize the way the RadioSelect
is rendered.
>>> w = RadioSelect()
>>> r = w.get_renderer('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
>>> for inp in r:
...     print inp
<label><input checked="checked" type="radio" name="beatle" value="J" /> John</label>
<label><input type="radio" name="beatle" value="P" /> Paul</label>
<label><input type="radio" name="beatle" value="G" /> George</label>
<label><input type="radio" name="beatle" value="R" /> Ringo</label>
>>> for inp in r:
...     print '%s<br />' % inp
<label><input checked="checked" type="radio" name="beatle" value="J" /> John</label><br />
<label><input type="radio" name="beatle" value="P" /> Paul</label><br />
<label><input type="radio" name="beatle" value="G" /> George</label><br />
<label><input type="radio" name="beatle" value="R" /> Ringo</label><br />
>>> for inp in r:
...     print '<p>%s %s</p>' % (inp.tag(), inp.choice_label)
<p><input checked="checked" type="radio" name="beatle" value="J" /> John</p>
<p><input type="radio" name="beatle" value="P" /> Paul</p>
<p><input type="radio" name="beatle" value="G" /> George</p>
<p><input type="radio" name="beatle" value="R" /> Ringo</p>
>>> for inp in r:
...     print '%s %s %s %s %s' % (inp.name, inp.value, inp.choice_value, inp.choice_label, inp.is_checked())
beatle J J John True
beatle J P Paul False
beatle J G George False
beatle J R Ringo False

You can create your own custom renderers for RadioSelect to use.
>>> class MyRenderer(RadioFieldRenderer):
...    def render(self):
...        return u'<br />\n'.join([unicode(choice) for choice in self])
>>> w = RadioSelect(renderer=MyRenderer)
>>> print w.render('beatle', 'G', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<label><input type="radio" name="beatle" value="J" /> John</label><br />
<label><input type="radio" name="beatle" value="P" /> Paul</label><br />
<label><input checked="checked" type="radio" name="beatle" value="G" /> George</label><br />
<label><input type="radio" name="beatle" value="R" /> Ringo</label>

Or you can use custom RadioSelect fields that use your custom renderer.
>>> class CustomRadioSelect(RadioSelect):
...    renderer = MyRenderer
>>> w = CustomRadioSelect()
>>> print w.render('beatle', 'G', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<label><input type="radio" name="beatle" value="J" /> John</label><br />
<label><input type="radio" name="beatle" value="P" /> Paul</label><br />
<label><input checked="checked" type="radio" name="beatle" value="G" /> George</label><br />
<label><input type="radio" name="beatle" value="R" /> Ringo</label>

A RadioFieldRenderer object also allows index access to individual RadioInput
objects.
>>> w = RadioSelect()
>>> r = w.get_renderer('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
>>> print r[1]
<label><input type="radio" name="beatle" value="P" /> Paul</label>
>>> print r[0]
<label><input checked="checked" type="radio" name="beatle" value="J" /> John</label>
>>> r[0].is_checked()
True
>>> r[1].is_checked()
False
>>> r[1].name, r[1].value, r[1].choice_value, r[1].choice_label
('beatle', u'J', u'P', u'Paul')
>>> r[10] # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
...
IndexError: list index out of range

# Choices are escaped correctly
>>> w = RadioSelect()
>>> print w.render('escape', None, choices=(('bad', 'you & me'), ('good', mark_safe('you &gt; me'))))
<ul>
<li><label><input type="radio" name="escape" value="bad" /> you &amp; me</label></li>
<li><label><input type="radio" name="escape" value="good" /> you &gt; me</label></li>
</ul>

# Unicode choices are correctly rendered as HTML
>>> w = RadioSelect()
>>> unicode(w.render('email', 'ŠĐĆŽćžšđ', choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')]))
u'<ul>\n<li><label><input checked="checked" type="radio" name="email" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" /> \u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111</label></li>\n<li><label><input type="radio" name="email" value="\u0107\u017e\u0161\u0111" /> abc\u0107\u017e\u0161\u0111</label></li>\n</ul>'

# Attributes provided at instantiation are passed to the constituent inputs
>>> w = RadioSelect(attrs={'id':'foo'})
>>> print w.render('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label for="foo_0"><input checked="checked" type="radio" id="foo_0" value="J" name="beatle" /> John</label></li>
<li><label for="foo_1"><input type="radio" id="foo_1" value="P" name="beatle" /> Paul</label></li>
<li><label for="foo_2"><input type="radio" id="foo_2" value="G" name="beatle" /> George</label></li>
<li><label for="foo_3"><input type="radio" id="foo_3" value="R" name="beatle" /> Ringo</label></li>
</ul>

# Attributes provided at render-time are passed to the constituent inputs
>>> w = RadioSelect()
>>> print w.render('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')), attrs={'id':'bar'})
<ul>
<li><label for="bar_0"><input checked="checked" type="radio" id="bar_0" value="J" name="beatle" /> John</label></li>
<li><label for="bar_1"><input type="radio" id="bar_1" value="P" name="beatle" /> Paul</label></li>
<li><label for="bar_2"><input type="radio" id="bar_2" value="G" name="beatle" /> George</label></li>
<li><label for="bar_3"><input type="radio" id="bar_3" value="R" name="beatle" /> Ringo</label></li>
</ul>

# CheckboxSelectMultiple Widget ###############################################

>>> w = CheckboxSelectMultiple()
>>> print w.render('beatles', ['J'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label><input checked="checked" type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>
>>> print w.render('beatles', ['J', 'P'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label><input checked="checked" type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input checked="checked" type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>
>>> print w.render('beatles', ['J', 'P', 'R'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label><input checked="checked" type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input checked="checked" type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input checked="checked" type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>

If the value is None, none of the options are selected:
>>> print w.render('beatles', None, choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label><input type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>

If the value corresponds to a label (but not to an option value), none of the options are selected:
>>> print w.render('beatles', ['John'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label><input type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>

If multiple values are given, but some of them are not valid, the valid ones are selected:
>>> print w.render('beatles', ['J', 'G', 'foo'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label><input checked="checked" type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input checked="checked" type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>

The value is compared to its str():
>>> print w.render('nums', [2], choices=[('1', '1'), ('2', '2'), ('3', '3')])
<ul>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
</ul>
>>> print w.render('nums', ['2'], choices=[(1, 1), (2, 2), (3, 3)])
<ul>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
</ul>
>>> print w.render('nums', [2], choices=[(1, 1), (2, 2), (3, 3)])
<ul>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
</ul>

The 'choices' argument can be any iterable:
>>> def get_choices():
...     for i in range(5):
...         yield (i, i)
>>> print w.render('nums', [2], choices=get_choices())
<ul>
<li><label><input type="checkbox" name="nums" value="0" /> 0</label></li>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
<li><label><input type="checkbox" name="nums" value="4" /> 4</label></li>
</ul>

You can also pass 'choices' to the constructor:
>>> w = CheckboxSelectMultiple(choices=[(1, 1), (2, 2), (3, 3)])
>>> print w.render('nums', [2])
<ul>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
</ul>

If 'choices' is passed to both the constructor and render(), then they'll both be in the output:
>>> print w.render('nums', [2], choices=[(4, 4), (5, 5)])
<ul>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
<li><label><input type="checkbox" name="nums" value="4" /> 4</label></li>
<li><label><input type="checkbox" name="nums" value="5" /> 5</label></li>
</ul>

# Choices are escaped correctly
>>> print w.render('escape', None, choices=(('bad', 'you & me'), ('good', mark_safe('you &gt; me'))))
<ul>
<li><label><input type="checkbox" name="escape" value="1" /> 1</label></li>
<li><label><input type="checkbox" name="escape" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="escape" value="3" /> 3</label></li>
<li><label><input type="checkbox" name="escape" value="bad" /> you &amp; me</label></li>
<li><label><input type="checkbox" name="escape" value="good" /> you &gt; me</label></li>
</ul>

# Test the usage of _has_changed
>>> w._has_changed(None, None)
False
>>> w._has_changed([], None)
False
>>> w._has_changed(None, [u'1'])
True
>>> w._has_changed([1, 2], [u'1', u'2'])
False
>>> w._has_changed([1, 2], [u'1'])
True
>>> w._has_changed([1, 2], [u'1', u'3'])
True

# Unicode choices are correctly rendered as HTML
>>> w.render('nums', ['ŠĐĆŽćžšđ'], choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')])
u'<ul>\n<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>\n<li><label><input type="checkbox" name="nums" value="2" /> 2</label></li>\n<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>\n<li><label><input checked="checked" type="checkbox" name="nums" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" /> \u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111</label></li>\n<li><label><input type="checkbox" name="nums" value="\u0107\u017e\u0161\u0111" /> abc\u0107\u017e\u0161\u0111</label></li>\n</ul>'

# MultiWidget #################################################################

>>> class MyMultiWidget(MultiWidget):
...     def decompress(self, value):
...         if value:
...             return value.split('__')
...         return ['', '']
...     def format_output(self, rendered_widgets):
...         return u'<br />'.join(rendered_widgets)
>>> w = MyMultiWidget(widgets=(TextInput(attrs={'class': 'big'}), TextInput(attrs={'class': 'small'})))
>>> w.render('name', ['john', 'lennon'])
u'<input type="text" class="big" value="john" name="name_0" /><br /><input type="text" class="small" value="lennon" name="name_1" />'
>>> w.render('name', 'john__lennon')
u'<input type="text" class="big" value="john" name="name_0" /><br /><input type="text" class="small" value="lennon" name="name_1" />'
>>> w.render('name', 'john__lennon', attrs={'id':'foo'})
u'<input id="foo_0" type="text" class="big" value="john" name="name_0" /><br /><input id="foo_1" type="text" class="small" value="lennon" name="name_1" />'
>>> w = MyMultiWidget(widgets=(TextInput(attrs={'class': 'big'}), TextInput(attrs={'class': 'small'})), attrs={'id': 'bar'})
>>> w.render('name', ['john', 'lennon'])
u'<input id="bar_0" type="text" class="big" value="john" name="name_0" /><br /><input id="bar_1" type="text" class="small" value="lennon" name="name_1" />'

>>> w = MyMultiWidget(widgets=(TextInput(), TextInput()))

# test with no initial data
>>> w._has_changed(None, [u'john', u'lennon'])
True

# test when the data is the same as initial
>>> w._has_changed(u'john__lennon', [u'john', u'lennon'])
False

# test when the first widget's data has changed
>>> w._has_changed(u'john__lennon', [u'alfred', u'lennon'])
True

# test when the last widget's data has changed. this ensures that it is not
# short circuiting while testing the widgets.
>>> w._has_changed(u'john__lennon', [u'john', u'denver'])
True

# SplitDateTimeWidget #########################################################

>>> w = SplitDateTimeWidget()
>>> w.render('date', '')
u'<input type="text" name="date_0" /><input type="text" name="date_1" />'
>>> w.render('date', None)
u'<input type="text" name="date_0" /><input type="text" name="date_1" />'
>>> w.render('date', datetime.datetime(2006, 1, 10, 7, 30))
u'<input type="text" name="date_0" value="2006-01-10" /><input type="text" name="date_1" value="07:30:00" />'
>>> w.render('date', [datetime.date(2006, 1, 10), datetime.time(7, 30)])
u'<input type="text" name="date_0" value="2006-01-10" /><input type="text" name="date_1" value="07:30:00" />'

You can also pass 'attrs' to the constructor. In this case, the attrs will be
included on both widgets.
>>> w = SplitDateTimeWidget(attrs={'class': 'pretty'})
>>> w.render('date', datetime.datetime(2006, 1, 10, 7, 30))
u'<input type="text" class="pretty" value="2006-01-10" name="date_0" /><input type="text" class="pretty" value="07:30:00" name="date_1" />'

Use 'date_format' and 'time_format' to change the way a value is displayed.
>>> w = SplitDateTimeWidget(date_format='%d/%m/%Y', time_format='%H:%M')
>>> w.render('date', datetime.datetime(2006, 1, 10, 7, 30))
u'<input type="text" name="date_0" value="10/01/2006" /><input type="text" name="date_1" value="07:30" />'

>>> w._has_changed(datetime.datetime(2008, 5, 5, 12, 40, 00), [u'2008-05-05', u'12:40:00'])
False
>>> w._has_changed(datetime.datetime(2008, 5, 5, 12, 40, 00), [u'2008-05-05', u'12:41:00'])
True

# DateTimeInput ###############################################################

>>> w = DateTimeInput()
>>> w.render('date', None)
u'<input type="text" name="date" />'
>>> d = datetime.datetime(2007, 9, 17, 12, 51, 34, 482548)
>>> print d
2007-09-17 12:51:34.482548

The microseconds are trimmed on display, by default.
>>> w.render('date', d)
u'<input type="text" name="date" value="2007-09-17 12:51:34" />'
>>> w.render('date', datetime.datetime(2007, 9, 17, 12, 51, 34))
u'<input type="text" name="date" value="2007-09-17 12:51:34" />'
>>> w.render('date', datetime.datetime(2007, 9, 17, 12, 51))
u'<input type="text" name="date" value="2007-09-17 12:51:00" />'

Use 'format' to change the way a value is displayed.
>>> w = DateTimeInput(format='%d/%m/%Y %H:%M')
>>> w.render('date', d)
u'<input type="text" name="date" value="17/09/2007 12:51" />'

# DateInput ###################################################################

>>> w = DateInput()
>>> w.render('date', None)
u'<input type="text" name="date" />'
>>> d = datetime.date(2007, 9, 17)
>>> print d
2007-09-17

>>> w.render('date', d)
u'<input type="text" name="date" value="2007-09-17" />'
>>> w.render('date', datetime.date(2007, 9, 17))
u'<input type="text" name="date" value="2007-09-17" />'

We should be able to initialize from a unicode value.
>>> w.render('date', u'2007-09-17')
u'<input type="text" name="date" value="2007-09-17" />'

Use 'format' to change the way a value is displayed.
>>> w = DateInput(format='%d/%m/%Y')
>>> w.render('date', d)
u'<input type="text" name="date" value="17/09/2007" />'

# TimeInput ###################################################################

>>> w = TimeInput()
>>> w.render('time', None)
u'<input type="text" name="time" />'
>>> t = datetime.time(12, 51, 34, 482548)
>>> print t
12:51:34.482548

The microseconds are trimmed on display, by default.
>>> w.render('time', t)
u'<input type="text" name="time" value="12:51:34" />'
>>> w.render('time', datetime.time(12, 51, 34))
u'<input type="text" name="time" value="12:51:34" />'
>>> w.render('time', datetime.time(12, 51))
u'<input type="text" name="time" value="12:51:00" />'

We should be able to initialize from a unicode value.
>>> w.render('time', u'13:12:11')
u'<input type="text" name="time" value="13:12:11" />'

Use 'format' to change the way a value is displayed.
>>> w = TimeInput(format='%H:%M')
>>> w.render('time', t)
u'<input type="text" name="time" value="12:51" />'

# SplitHiddenDateTimeWidget ###################################################

>>> from django.forms.widgets import SplitHiddenDateTimeWidget

>>> w = SplitHiddenDateTimeWidget()
>>> w.render('date', '')
u'<input type="hidden" name="date_0" /><input type="hidden" name="date_1" />'
>>> d = datetime.datetime(2007, 9, 17, 12, 51, 34, 482548)
>>> print d
2007-09-17 12:51:34.482548
>>> w.render('date', d)
u'<input type="hidden" name="date_0" value="2007-09-17" /><input type="hidden" name="date_1" value="12:51:34" />'
>>> w.render('date', datetime.datetime(2007, 9, 17, 12, 51, 34))
u'<input type="hidden" name="date_0" value="2007-09-17" /><input type="hidden" name="date_1" value="12:51:34" />'
>>> w.render('date', datetime.datetime(2007, 9, 17, 12, 51))
u'<input type="hidden" name="date_0" value="2007-09-17" /><input type="hidden" name="date_1" value="12:51:00" />'

"""

