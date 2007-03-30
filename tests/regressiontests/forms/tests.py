# -*- coding: utf-8 -*-
r"""
>>> from django.newforms import *
>>> import datetime
>>> import re

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

>>> w = FileInput()
>>> w.render('email', '')
u'<input type="file" name="email" />'
>>> w.render('email', None)
u'<input type="file" name="email" />'
>>> w.render('email', 'test@example.com')
u'<input type="file" name="email" value="test@example.com" />'
>>> w.render('email', 'some "quoted" & ampersanded value')
u'<input type="file" name="email" value="some &quot;quoted&quot; &amp; ampersanded value" />'
>>> w.render('email', 'test@example.com', attrs={'class': 'fun'})
u'<input type="file" name="email" value="test@example.com" class="fun" />'

You can also pass 'attrs' to the constructor:
>>> w = FileInput(attrs={'class': 'fun'})
>>> w.render('email', '')
u'<input type="file" class="fun" name="email" />'
>>> w.render('email', 'foo@example.com')
u'<input type="file" class="fun" value="foo@example.com" name="email" />'

>>> w.render('email', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'})
u'<input type="file" class="fun" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" name="email" />'

# Textarea Widget #############################################################

>>> w = Textarea()
>>> w.render('msg', '')
u'<textarea name="msg"></textarea>'
>>> w.render('msg', None)
u'<textarea name="msg"></textarea>'
>>> w.render('msg', 'value')
u'<textarea name="msg">value</textarea>'
>>> w.render('msg', 'some "quoted" & ampersanded value')
u'<textarea name="msg">some &quot;quoted&quot; &amp; ampersanded value</textarea>'
>>> w.render('msg', 'value', attrs={'class': 'pretty'})
u'<textarea name="msg" class="pretty">value</textarea>'

You can also pass 'attrs' to the constructor:
>>> w = Textarea(attrs={'class': 'pretty'})
>>> w.render('msg', '')
u'<textarea class="pretty" name="msg"></textarea>'
>>> w.render('msg', 'example')
u'<textarea class="pretty" name="msg">example</textarea>'

'attrs' passed to render() get precedence over those passed to the constructor:
>>> w = Textarea(attrs={'class': 'pretty'})
>>> w.render('msg', '', attrs={'class': 'special'})
u'<textarea class="special" name="msg"></textarea>'

>>> w.render('msg', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'})
u'<textarea class="fun" name="msg">\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111</textarea>'

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

>>> w.render('nums', ['ŠĐĆŽćžšđ'], choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')])
u'<select multiple="multiple" name="nums">\n<option value="1">1</option>\n<option value="2">2</option>\n<option value="3">3</option>\n<option value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" selected="selected">\u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111</option>\n<option value="\u0107\u017e\u0161\u0111">abc\u0107\u017e\u0161\u0111</option>\n</select>'

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

The render() method returns a RadioFieldRenderer object, whose str() is a <ul>.
You can manipulate that object directly to customize the way the RadioSelect
is rendered.
>>> w = RadioSelect()
>>> r = w.render('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
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

A RadioFieldRenderer object also allows index access to individual RadioInput
objects.
>>> w = RadioSelect()
>>> r = w.render('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
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
>>> r[10]
Traceback (most recent call last):
...
IndexError: list index out of range

>>> w = RadioSelect()
>>> unicode(w.render('email', 'ŠĐĆŽćžšđ', choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')]))
u'<ul>\n<li><label><input checked="checked" type="radio" name="email" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" /> \u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111</label></li>\n<li><label><input type="radio" name="email" value="\u0107\u017e\u0161\u0111" /> abc\u0107\u017e\u0161\u0111</label></li>\n</ul>'

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

##########
# Fields #
##########

Each Field class does some sort of validation. Each Field has a clean() method,
which either raises django.newforms.ValidationError or returns the "clean"
data -- usually a Unicode object, but, in some rare cases, a list.

Each Field's __init__() takes at least these parameters:
    required -- Boolean that specifies whether the field is required.
                True by default.
    widget -- A Widget class, or instance of a Widget class, that should be
              used for this Field when displaying it. Each Field has a default
              Widget that it'll use if you don't specify this. In most cases,
              the default widget is TextInput.
    label -- A verbose name for this field, for use in displaying this field in
             a form. By default, Django will use a "pretty" version of the form
             field name, if the Field is part of a Form.
    initial -- A value to use in this Field's initial display. This value is
               *not* used as a fallback if data isn't given.

Other than that, the Field subclasses have class-specific options for
__init__(). For example, CharField has a max_length option.

# CharField ###################################################################

>>> f = CharField()
>>> f.clean(1)
u'1'
>>> f.clean('hello')
u'hello'
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean([1, 2, 3])
u'[1, 2, 3]'

>>> f = CharField(required=False)
>>> f.clean(1)
u'1'
>>> f.clean('hello')
u'hello'
>>> f.clean(None)
u''
>>> f.clean('')
u''
>>> f.clean([1, 2, 3])
u'[1, 2, 3]'

CharField accepts an optional max_length parameter:
>>> f = CharField(max_length=10, required=False)
>>> f.clean('12345')
u'12345'
>>> f.clean('1234567890')
u'1234567890'
>>> f.clean('1234567890a')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 10 characters.']

CharField accepts an optional min_length parameter:
>>> f = CharField(min_length=10, required=False)
>>> f.clean('')
u''
>>> f.clean('12345')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 10 characters.']
>>> f.clean('1234567890')
u'1234567890'
>>> f.clean('1234567890a')
u'1234567890a'

>>> f = CharField(min_length=10, required=True)
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('12345')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 10 characters.']
>>> f.clean('1234567890')
u'1234567890'
>>> f.clean('1234567890a')
u'1234567890a'

# IntegerField ################################################################

>>> f = IntegerField()
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('1')
1
>>> isinstance(f.clean('1'), int)
True
>>> f.clean('23')
23
>>> f.clean('a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a whole number.']
>>> f.clean('1 ')
1
>>> f.clean(' 1')
1
>>> f.clean(' 1 ')
1
>>> f.clean('1a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a whole number.']

>>> f = IntegerField(required=False)
>>> f.clean('')
>>> repr(f.clean(''))
'None'
>>> f.clean(None)
>>> repr(f.clean(None))
'None'
>>> f.clean('1')
1
>>> isinstance(f.clean('1'), int)
True
>>> f.clean('23')
23
>>> f.clean('a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a whole number.']
>>> f.clean('1 ')
1
>>> f.clean(' 1')
1
>>> f.clean(' 1 ')
1
>>> f.clean('1a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a whole number.']

IntegerField accepts an optional max_value parameter:
>>> f = IntegerField(max_value=10)
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(1)
1
>>> f.clean(10)
10
>>> f.clean(11)
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value is less than or equal to 10.']
>>> f.clean('10')
10
>>> f.clean('11')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value is less than or equal to 10.']

IntegerField accepts an optional min_value parameter:
>>> f = IntegerField(min_value=10)
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(1)
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value is greater than or equal to 10.']
>>> f.clean(10)
10
>>> f.clean(11)
11
>>> f.clean('10')
10
>>> f.clean('11')
11

min_value and max_value can be used together:
>>> f = IntegerField(min_value=10, max_value=20)
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(1)
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value is greater than or equal to 10.']
>>> f.clean(10)
10
>>> f.clean(11)
11
>>> f.clean('10')
10
>>> f.clean('11')
11
>>> f.clean(20)
20
>>> f.clean(21)
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value is less than or equal to 20.']

# DateField ###################################################################

>>> import datetime
>>> f = DateField()
>>> f.clean(datetime.date(2006, 10, 25))
datetime.date(2006, 10, 25)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30))
datetime.date(2006, 10, 25)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59))
datetime.date(2006, 10, 25)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59, 200))
datetime.date(2006, 10, 25)
>>> f.clean('2006-10-25')
datetime.date(2006, 10, 25)
>>> f.clean('10/25/2006')
datetime.date(2006, 10, 25)
>>> f.clean('10/25/06')
datetime.date(2006, 10, 25)
>>> f.clean('Oct 25 2006')
datetime.date(2006, 10, 25)
>>> f.clean('October 25 2006')
datetime.date(2006, 10, 25)
>>> f.clean('October 25, 2006')
datetime.date(2006, 10, 25)
>>> f.clean('25 October 2006')
datetime.date(2006, 10, 25)
>>> f.clean('25 October, 2006')
datetime.date(2006, 10, 25)
>>> f.clean('2006-4-31')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.clean('200a-10-25')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.clean('25/10/06')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = DateField(required=False)
>>> f.clean(None)
>>> repr(f.clean(None))
'None'
>>> f.clean('')
>>> repr(f.clean(''))
'None'

DateField accepts an optional input_formats parameter:
>>> f = DateField(input_formats=['%Y %m %d'])
>>> f.clean(datetime.date(2006, 10, 25))
datetime.date(2006, 10, 25)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30))
datetime.date(2006, 10, 25)
>>> f.clean('2006 10 25')
datetime.date(2006, 10, 25)

The input_formats parameter overrides all default input formats,
so the default formats won't work unless you specify them:
>>> f.clean('2006-10-25')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.clean('10/25/2006')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.clean('10/25/06')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']

# TimeField ###################################################################

>>> import datetime
>>> f = TimeField()
>>> f.clean(datetime.time(14, 25))
datetime.time(14, 25)
>>> f.clean(datetime.time(14, 25, 59))
datetime.time(14, 25, 59)
>>> f.clean('14:25')
datetime.time(14, 25)
>>> f.clean('14:25:59')
datetime.time(14, 25, 59)
>>> f.clean('hello')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid time.']
>>> f.clean('1:24 p.m.')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid time.']

TimeField accepts an optional input_formats parameter:
>>> f = TimeField(input_formats=['%I:%M %p'])
>>> f.clean(datetime.time(14, 25))
datetime.time(14, 25)
>>> f.clean(datetime.time(14, 25, 59))
datetime.time(14, 25, 59)
>>> f.clean('4:25 AM')
datetime.time(4, 25)
>>> f.clean('4:25 PM')
datetime.time(16, 25)

The input_formats parameter overrides all default input formats,
so the default formats won't work unless you specify them:
>>> f.clean('14:30:45')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid time.']

# DateTimeField ###############################################################

>>> import datetime
>>> f = DateTimeField()
>>> f.clean(datetime.date(2006, 10, 25))
datetime.datetime(2006, 10, 25, 0, 0)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30))
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59))
datetime.datetime(2006, 10, 25, 14, 30, 59)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59, 200))
datetime.datetime(2006, 10, 25, 14, 30, 59, 200)
>>> f.clean('2006-10-25 14:30:45')
datetime.datetime(2006, 10, 25, 14, 30, 45)
>>> f.clean('2006-10-25 14:30:00')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean('2006-10-25 14:30')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean('2006-10-25')
datetime.datetime(2006, 10, 25, 0, 0)
>>> f.clean('10/25/2006 14:30:45')
datetime.datetime(2006, 10, 25, 14, 30, 45)
>>> f.clean('10/25/2006 14:30:00')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean('10/25/2006 14:30')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean('10/25/2006')
datetime.datetime(2006, 10, 25, 0, 0)
>>> f.clean('10/25/06 14:30:45')
datetime.datetime(2006, 10, 25, 14, 30, 45)
>>> f.clean('10/25/06 14:30:00')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean('10/25/06 14:30')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean('10/25/06')
datetime.datetime(2006, 10, 25, 0, 0)
>>> f.clean('hello')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date/time.']
>>> f.clean('2006-10-25 4:30 p.m.')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date/time.']

DateField accepts an optional input_formats parameter:
>>> f = DateTimeField(input_formats=['%Y %m %d %I:%M %p'])
>>> f.clean(datetime.date(2006, 10, 25))
datetime.datetime(2006, 10, 25, 0, 0)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30))
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59))
datetime.datetime(2006, 10, 25, 14, 30, 59)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59, 200))
datetime.datetime(2006, 10, 25, 14, 30, 59, 200)
>>> f.clean('2006 10 25 2:30 PM')
datetime.datetime(2006, 10, 25, 14, 30)

The input_formats parameter overrides all default input formats,
so the default formats won't work unless you specify them:
>>> f.clean('2006-10-25 14:30:45')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date/time.']

>>> f = DateTimeField(required=False)
>>> f.clean(None)
>>> repr(f.clean(None))
'None'
>>> f.clean('')
>>> repr(f.clean(''))
'None'

# RegexField ##################################################################

>>> f = RegexField('^\d[A-F]\d$')
>>> f.clean('2A2')
u'2A2'
>>> f.clean('3F3')
u'3F3'
>>> f.clean('3G3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.clean(' 2A2')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.clean('2A2 ')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = RegexField('^\d[A-F]\d$', required=False)
>>> f.clean('2A2')
u'2A2'
>>> f.clean('3F3')
u'3F3'
>>> f.clean('3G3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.clean('')
u''

Alternatively, RegexField can take a compiled regular expression:
>>> f = RegexField(re.compile('^\d[A-F]\d$'))
>>> f.clean('2A2')
u'2A2'
>>> f.clean('3F3')
u'3F3'
>>> f.clean('3G3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.clean(' 2A2')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.clean('2A2 ')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']

RegexField takes an optional error_message argument:
>>> f = RegexField('^\d\d\d\d$', error_message='Enter a four-digit number.')
>>> f.clean('1234')
u'1234'
>>> f.clean('123')
Traceback (most recent call last):
...
ValidationError: [u'Enter a four-digit number.']
>>> f.clean('abcd')
Traceback (most recent call last):
...
ValidationError: [u'Enter a four-digit number.']

RegexField also access min_length and max_length parameters, for convenience.
>>> f = RegexField('^\d+$', min_length=5, max_length=10)
>>> f.clean('123')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 5 characters.']
>>> f.clean('abc')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 5 characters.']
>>> f.clean('12345')
u'12345'
>>> f.clean('1234567890')
u'1234567890'
>>> f.clean('12345678901')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 10 characters.']
>>> f.clean('12345a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']

# EmailField ##################################################################

>>> f = EmailField()
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('person@example.com')
u'person@example.com'
>>> f.clean('foo')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']
>>> f.clean('foo@')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']
>>> f.clean('foo@bar')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']

>>> f = EmailField(required=False)
>>> f.clean('')
u''
>>> f.clean(None)
u''
>>> f.clean('person@example.com')
u'person@example.com'
>>> f.clean('foo')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']
>>> f.clean('foo@')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']
>>> f.clean('foo@bar')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']

EmailField also access min_length and max_length parameters, for convenience.
>>> f = EmailField(min_length=10, max_length=15)
>>> f.clean('a@foo.com')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 10 characters.']
>>> f.clean('alf@foo.com')
u'alf@foo.com'
>>> f.clean('alf123456788@foo.com')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 15 characters.']

# URLField ##################################################################

>>> f = URLField()
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('http://example.com')
u'http://example.com'
>>> f.clean('http://www.example.com')
u'http://www.example.com'
>>> f.clean('foo')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('example.com')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://example')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://example.')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://.com')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']

>>> f = URLField(required=False)
>>> f.clean('')
u''
>>> f.clean(None)
u''
>>> f.clean('http://example.com')
u'http://example.com'
>>> f.clean('http://www.example.com')
u'http://www.example.com'
>>> f.clean('foo')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('example.com')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://example')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://example.')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://.com')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']

URLField takes an optional verify_exists parameter, which is False by default.
This verifies that the URL is live on the Internet and doesn't return a 404 or 500:
>>> f = URLField(verify_exists=True)
>>> f.clean('http://www.google.com') # This will fail if there's no Internet connection
u'http://www.google.com'
>>> f.clean('http://example')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://www.jfoiwjfoi23jfoijoaijfoiwjofiwjefewl.com') # bad domain
Traceback (most recent call last):
...
ValidationError: [u'This URL appears to be a broken link.']
>>> f.clean('http://google.com/we-love-microsoft.html') # good domain, bad page
Traceback (most recent call last):
...
ValidationError: [u'This URL appears to be a broken link.']
>>> f = URLField(verify_exists=True, required=False)
>>> f.clean('')
u''
>>> f.clean('http://www.google.com') # This will fail if there's no Internet connection
u'http://www.google.com'

EmailField also access min_length and max_length parameters, for convenience.
>>> f = URLField(min_length=15, max_length=20)
>>> f.clean('http://f.com')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 15 characters.']
>>> f.clean('http://example.com')
u'http://example.com'
>>> f.clean('http://abcdefghijklmnopqrstuvwxyz.com')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 20 characters.']

# BooleanField ################################################################

>>> f = BooleanField()
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(True)
True
>>> f.clean(False)
False
>>> f.clean(1)
True
>>> f.clean(0)
False
>>> f.clean('Django rocks')
True

>>> f = BooleanField(required=False)
>>> f.clean('')
False
>>> f.clean(None)
False
>>> f.clean(True)
True
>>> f.clean(False)
False
>>> f.clean(1)
True
>>> f.clean(0)
False
>>> f.clean('Django rocks')
True

# ChoiceField #################################################################

>>> f = ChoiceField(choices=[('1', '1'), ('2', '2')])
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(1)
u'1'
>>> f.clean('1')
u'1'
>>> f.clean('3')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. That choice is not one of the available choices.']

>>> f = ChoiceField(choices=[('1', '1'), ('2', '2')], required=False)
>>> f.clean('')
u''
>>> f.clean(None)
u''
>>> f.clean(1)
u'1'
>>> f.clean('1')
u'1'
>>> f.clean('3')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. That choice is not one of the available choices.']

>>> f = ChoiceField(choices=[('J', 'John'), ('P', 'Paul')])
>>> f.clean('J')
u'J'
>>> f.clean('John')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. That choice is not one of the available choices.']

# NullBooleanField ############################################################

>>> f = NullBooleanField()
>>> f.clean('')
>>> f.clean(True)
True
>>> f.clean(False)
False
>>> f.clean(None)
>>> f.clean('1')
>>> f.clean('2')
>>> f.clean('3')
>>> f.clean('hello')

# MultipleChoiceField #########################################################

>>> f = MultipleChoiceField(choices=[('1', '1'), ('2', '2')])
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean([1])
[u'1']
>>> f.clean(['1'])
[u'1']
>>> f.clean(['1', '2'])
[u'1', u'2']
>>> f.clean([1, '2'])
[u'1', u'2']
>>> f.clean((1, '2'))
[u'1', u'2']
>>> f.clean('hello')
Traceback (most recent call last):
...
ValidationError: [u'Enter a list of values.']
>>> f.clean([])
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(())
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(['3'])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 3 is not one of the available choices.']

>>> f = MultipleChoiceField(choices=[('1', '1'), ('2', '2')], required=False)
>>> f.clean('')
[]
>>> f.clean(None)
[]
>>> f.clean([1])
[u'1']
>>> f.clean(['1'])
[u'1']
>>> f.clean(['1', '2'])
[u'1', u'2']
>>> f.clean([1, '2'])
[u'1', u'2']
>>> f.clean((1, '2'))
[u'1', u'2']
>>> f.clean('hello')
Traceback (most recent call last):
...
ValidationError: [u'Enter a list of values.']
>>> f.clean([])
[]
>>> f.clean(())
[]
>>> f.clean(['3'])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 3 is not one of the available choices.']

# ComboField ##################################################################

ComboField takes a list of fields that should be used to validate a value,
in that order.
>>> f = ComboField(fields=[CharField(max_length=20), EmailField()])
>>> f.clean('test@example.com')
u'test@example.com'
>>> f.clean('longemailaddress@example.com')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 20 characters.']
>>> f.clean('not an e-mail')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = ComboField(fields=[CharField(max_length=20), EmailField()], required=False)
>>> f.clean('test@example.com')
u'test@example.com'
>>> f.clean('longemailaddress@example.com')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 20 characters.']
>>> f.clean('not an e-mail')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']
>>> f.clean('')
u''
>>> f.clean(None)
u''

# SplitDateTimeField ##########################################################

>>> f = SplitDateTimeField()
>>> f.clean([datetime.date(2006, 1, 10), datetime.time(7, 30)])
datetime.datetime(2006, 1, 10, 7, 30)
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('hello')
Traceback (most recent call last):
...
ValidationError: [u'Enter a list of values.']
>>> f.clean(['hello', 'there'])
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.', u'Enter a valid time.']
>>> f.clean(['2006-01-10', 'there'])
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid time.']
>>> f.clean(['hello', '07:30'])
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']

>>> f = SplitDateTimeField(required=False)
>>> f.clean([datetime.date(2006, 1, 10), datetime.time(7, 30)])
datetime.datetime(2006, 1, 10, 7, 30)
>>> f.clean(None)
>>> f.clean('')
>>> f.clean('hello')
Traceback (most recent call last):
...
ValidationError: [u'Enter a list of values.']
>>> f.clean(['hello', 'there'])
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.', u'Enter a valid time.']
>>> f.clean(['2006-01-10', 'there'])
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid time.']
>>> f.clean(['hello', '07:30'])
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']

#########
# Forms #
#########

A Form is a collection of Fields. It knows how to validate a set of data and it
knows how to render itself in a couple of default ways (e.g., an HTML table).
You can pass it data in __init__(), as a dictionary.

# Form ########################################################################

>>> class Person(Form):
...     first_name = CharField()
...     last_name = CharField()
...     birthday = DateField()

Pass a dictionary to a Form's __init__().
>>> p = Person({'first_name': u'John', 'last_name': u'Lennon', 'birthday': u'1940-10-9'})
>>> p.is_bound
True
>>> p.errors
{}
>>> p.is_valid()
True
>>> p.errors.as_ul()
u''
>>> p.errors.as_text()
u''
>>> p.clean_data
{'first_name': u'John', 'last_name': u'Lennon', 'birthday': datetime.date(1940, 10, 9)}
>>> print p['first_name']
<input type="text" name="first_name" value="John" id="id_first_name" />
>>> print p['last_name']
<input type="text" name="last_name" value="Lennon" id="id_last_name" />
>>> print p['birthday']
<input type="text" name="birthday" value="1940-10-9" id="id_birthday" />
>>> print p['nonexistentfield']
Traceback (most recent call last):
...
KeyError: "Key 'nonexistentfield' not found in Form"

>>> for boundfield in p:
...     print boundfield
<input type="text" name="first_name" value="John" id="id_first_name" />
<input type="text" name="last_name" value="Lennon" id="id_last_name" />
<input type="text" name="birthday" value="1940-10-9" id="id_birthday" />
>>> for boundfield in p:
...     print boundfield.label, boundfield.data
First name John
Last name Lennon
Birthday 1940-10-9
>>> print p
<tr><th><label for="id_first_name">First name:</label></th><td><input type="text" name="first_name" value="John" id="id_first_name" /></td></tr>
<tr><th><label for="id_last_name">Last name:</label></th><td><input type="text" name="last_name" value="Lennon" id="id_last_name" /></td></tr>
<tr><th><label for="id_birthday">Birthday:</label></th><td><input type="text" name="birthday" value="1940-10-9" id="id_birthday" /></td></tr>

Empty dictionaries are valid, too.
>>> p = Person({})
>>> p.is_bound
True
>>> p.errors
{'first_name': [u'This field is required.'], 'last_name': [u'This field is required.'], 'birthday': [u'This field is required.']}
>>> p.is_valid()
False
>>> p.clean_data
Traceback (most recent call last):
...
AttributeError: 'Person' object has no attribute 'clean_data'
>>> print p
<tr><th><label for="id_first_name">First name:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="first_name" id="id_first_name" /></td></tr>
<tr><th><label for="id_last_name">Last name:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="last_name" id="id_last_name" /></td></tr>
<tr><th><label for="id_birthday">Birthday:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="birthday" id="id_birthday" /></td></tr>
>>> print p.as_table()
<tr><th><label for="id_first_name">First name:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="first_name" id="id_first_name" /></td></tr>
<tr><th><label for="id_last_name">Last name:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="last_name" id="id_last_name" /></td></tr>
<tr><th><label for="id_birthday">Birthday:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="birthday" id="id_birthday" /></td></tr>
>>> print p.as_ul()
<li><ul class="errorlist"><li>This field is required.</li></ul><label for="id_first_name">First name:</label> <input type="text" name="first_name" id="id_first_name" /></li>
<li><ul class="errorlist"><li>This field is required.</li></ul><label for="id_last_name">Last name:</label> <input type="text" name="last_name" id="id_last_name" /></li>
<li><ul class="errorlist"><li>This field is required.</li></ul><label for="id_birthday">Birthday:</label> <input type="text" name="birthday" id="id_birthday" /></li>
>>> print p.as_p()
<p><ul class="errorlist"><li>This field is required.</li></ul></p>
<p><label for="id_first_name">First name:</label> <input type="text" name="first_name" id="id_first_name" /></p>
<p><ul class="errorlist"><li>This field is required.</li></ul></p>
<p><label for="id_last_name">Last name:</label> <input type="text" name="last_name" id="id_last_name" /></p>
<p><ul class="errorlist"><li>This field is required.</li></ul></p>
<p><label for="id_birthday">Birthday:</label> <input type="text" name="birthday" id="id_birthday" /></p>

If you don't pass any values to the Form's __init__(), or if you pass None,
the Form will be considered unbound and won't do any validation. Form.errors
will be an empty dictionary *but* Form.is_valid() will return False.
>>> p = Person()
>>> p.is_bound
False
>>> p.errors
{}
>>> p.is_valid()
False
>>> p.clean_data
Traceback (most recent call last):
...
AttributeError: 'Person' object has no attribute 'clean_data'
>>> print p
<tr><th><label for="id_first_name">First name:</label></th><td><input type="text" name="first_name" id="id_first_name" /></td></tr>
<tr><th><label for="id_last_name">Last name:</label></th><td><input type="text" name="last_name" id="id_last_name" /></td></tr>
<tr><th><label for="id_birthday">Birthday:</label></th><td><input type="text" name="birthday" id="id_birthday" /></td></tr>
>>> print p.as_table()
<tr><th><label for="id_first_name">First name:</label></th><td><input type="text" name="first_name" id="id_first_name" /></td></tr>
<tr><th><label for="id_last_name">Last name:</label></th><td><input type="text" name="last_name" id="id_last_name" /></td></tr>
<tr><th><label for="id_birthday">Birthday:</label></th><td><input type="text" name="birthday" id="id_birthday" /></td></tr>
>>> print p.as_ul()
<li><label for="id_first_name">First name:</label> <input type="text" name="first_name" id="id_first_name" /></li>
<li><label for="id_last_name">Last name:</label> <input type="text" name="last_name" id="id_last_name" /></li>
<li><label for="id_birthday">Birthday:</label> <input type="text" name="birthday" id="id_birthday" /></li>
>>> print p.as_p()
<p><label for="id_first_name">First name:</label> <input type="text" name="first_name" id="id_first_name" /></p>
<p><label for="id_last_name">Last name:</label> <input type="text" name="last_name" id="id_last_name" /></p>
<p><label for="id_birthday">Birthday:</label> <input type="text" name="birthday" id="id_birthday" /></p>

Unicode values are handled properly.
>>> p = Person({'first_name': u'John', 'last_name': u'\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111', 'birthday': '1940-10-9'})
>>> p.as_table()
u'<tr><th><label for="id_first_name">First name:</label></th><td><input type="text" name="first_name" value="John" id="id_first_name" /></td></tr>\n<tr><th><label for="id_last_name">Last name:</label></th><td><input type="text" name="last_name" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" id="id_last_name" /></td></tr>\n<tr><th><label for="id_birthday">Birthday:</label></th><td><input type="text" name="birthday" value="1940-10-9" id="id_birthday" /></td></tr>'
>>> p.as_ul()
u'<li><label for="id_first_name">First name:</label> <input type="text" name="first_name" value="John" id="id_first_name" /></li>\n<li><label for="id_last_name">Last name:</label> <input type="text" name="last_name" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" id="id_last_name" /></li>\n<li><label for="id_birthday">Birthday:</label> <input type="text" name="birthday" value="1940-10-9" id="id_birthday" /></li>'
>>> p.as_p()
u'<p><label for="id_first_name">First name:</label> <input type="text" name="first_name" value="John" id="id_first_name" /></p>\n<p><label for="id_last_name">Last name:</label> <input type="text" name="last_name" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" id="id_last_name" /></p>\n<p><label for="id_birthday">Birthday:</label> <input type="text" name="birthday" value="1940-10-9" id="id_birthday" /></p>'

>>> p = Person({'last_name': u'Lennon'})
>>> p.errors
{'first_name': [u'This field is required.'], 'birthday': [u'This field is required.']}
>>> p.is_valid()
False
>>> p.errors.as_ul()
u'<ul class="errorlist"><li>first_name<ul class="errorlist"><li>This field is required.</li></ul></li><li>birthday<ul class="errorlist"><li>This field is required.</li></ul></li></ul>'
>>> print p.errors.as_text()
* first_name
  * This field is required.
* birthday
  * This field is required.
>>> p.clean_data
Traceback (most recent call last):
...
AttributeError: 'Person' object has no attribute 'clean_data'
>>> p['first_name'].errors
[u'This field is required.']
>>> p['first_name'].errors.as_ul()
u'<ul class="errorlist"><li>This field is required.</li></ul>'
>>> p['first_name'].errors.as_text()
u'* This field is required.'

>>> p = Person()
>>> print p['first_name']
<input type="text" name="first_name" id="id_first_name" />
>>> print p['last_name']
<input type="text" name="last_name" id="id_last_name" />
>>> print p['birthday']
<input type="text" name="birthday" id="id_birthday" />

clean_data will always *only* contain a key for fields defined in the
Form, even if you pass extra data when you define the Form. In this
example, we pass a bunch of extra fields to the form constructor,
but clean_data contains only the form's fields.
>>> data = {'first_name': u'John', 'last_name': u'Lennon', 'birthday': u'1940-10-9', 'extra1': 'hello', 'extra2': 'hello'}
>>> p = Person(data)
>>> p.is_valid()
True
>>> p.clean_data
{'first_name': u'John', 'last_name': u'Lennon', 'birthday': datetime.date(1940, 10, 9)}

"auto_id" tells the Form to add an "id" attribute to each form element.
If it's a string that contains '%s', Django will use that as a format string
into which the field's name will be inserted. It will also put a <label> around
the human-readable labels for a field.
>>> p = Person(auto_id='%s_id')
>>> print p.as_table()
<tr><th><label for="first_name_id">First name:</label></th><td><input type="text" name="first_name" id="first_name_id" /></td></tr>
<tr><th><label for="last_name_id">Last name:</label></th><td><input type="text" name="last_name" id="last_name_id" /></td></tr>
<tr><th><label for="birthday_id">Birthday:</label></th><td><input type="text" name="birthday" id="birthday_id" /></td></tr>
>>> print p.as_ul()
<li><label for="first_name_id">First name:</label> <input type="text" name="first_name" id="first_name_id" /></li>
<li><label for="last_name_id">Last name:</label> <input type="text" name="last_name" id="last_name_id" /></li>
<li><label for="birthday_id">Birthday:</label> <input type="text" name="birthday" id="birthday_id" /></li>
>>> print p.as_p()
<p><label for="first_name_id">First name:</label> <input type="text" name="first_name" id="first_name_id" /></p>
<p><label for="last_name_id">Last name:</label> <input type="text" name="last_name" id="last_name_id" /></p>
<p><label for="birthday_id">Birthday:</label> <input type="text" name="birthday" id="birthday_id" /></p>

If auto_id is any True value whose str() does not contain '%s', the "id"
attribute will be the name of the field.
>>> p = Person(auto_id=True)
>>> print p.as_ul()
<li><label for="first_name">First name:</label> <input type="text" name="first_name" id="first_name" /></li>
<li><label for="last_name">Last name:</label> <input type="text" name="last_name" id="last_name" /></li>
<li><label for="birthday">Birthday:</label> <input type="text" name="birthday" id="birthday" /></li>

If auto_id is any False value, an "id" attribute won't be output unless it
was manually entered.
>>> p = Person(auto_id=False)
>>> print p.as_ul()
<li>First name: <input type="text" name="first_name" /></li>
<li>Last name: <input type="text" name="last_name" /></li>
<li>Birthday: <input type="text" name="birthday" /></li>

In this example, auto_id is False, but the "id" attribute for the "first_name"
field is given. Also note that field gets a <label>, while the others don't.
>>> class PersonNew(Form):
...     first_name = CharField(widget=TextInput(attrs={'id': 'first_name_id'}))
...     last_name = CharField()
...     birthday = DateField()
>>> p = PersonNew(auto_id=False)
>>> print p.as_ul()
<li><label for="first_name_id">First name:</label> <input type="text" id="first_name_id" name="first_name" /></li>
<li>Last name: <input type="text" name="last_name" /></li>
<li>Birthday: <input type="text" name="birthday" /></li>

If the "id" attribute is specified in the Form and auto_id is True, the "id"
attribute in the Form gets precedence.
>>> p = PersonNew(auto_id=True)
>>> print p.as_ul()
<li><label for="first_name_id">First name:</label> <input type="text" id="first_name_id" name="first_name" /></li>
<li><label for="last_name">Last name:</label> <input type="text" name="last_name" id="last_name" /></li>
<li><label for="birthday">Birthday:</label> <input type="text" name="birthday" id="birthday" /></li>

>>> class SignupForm(Form):
...     email = EmailField()
...     get_spam = BooleanField()
>>> f = SignupForm(auto_id=False)
>>> print f['email']
<input type="text" name="email" />
>>> print f['get_spam']
<input type="checkbox" name="get_spam" />

>>> f = SignupForm({'email': 'test@example.com', 'get_spam': True}, auto_id=False)
>>> print f['email']
<input type="text" name="email" value="test@example.com" />
>>> print f['get_spam']
<input checked="checked" type="checkbox" name="get_spam" />

Any Field can have a Widget class passed to its constructor:
>>> class ContactForm(Form):
...     subject = CharField()
...     message = CharField(widget=Textarea)
>>> f = ContactForm(auto_id=False)
>>> print f['subject']
<input type="text" name="subject" />
>>> print f['message']
<textarea name="message"></textarea>

as_textarea(), as_text() and as_hidden() are shortcuts for changing the output
widget type:
>>> f['subject'].as_textarea()
u'<textarea name="subject"></textarea>'
>>> f['message'].as_text()
u'<input type="text" name="message" />'
>>> f['message'].as_hidden()
u'<input type="hidden" name="message" />'

The 'widget' parameter to a Field can also be an instance:
>>> class ContactForm(Form):
...     subject = CharField()
...     message = CharField(widget=Textarea(attrs={'rows': 80, 'cols': 20}))
>>> f = ContactForm(auto_id=False)
>>> print f['message']
<textarea rows="80" cols="20" name="message"></textarea>

Instance-level attrs are *not* carried over to as_textarea(), as_text() and
as_hidden():
>>> f['message'].as_text()
u'<input type="text" name="message" />'
>>> f = ContactForm({'subject': 'Hello', 'message': 'I love you.'}, auto_id=False)
>>> f['subject'].as_textarea()
u'<textarea name="subject">Hello</textarea>'
>>> f['message'].as_text()
u'<input type="text" name="message" value="I love you." />'
>>> f['message'].as_hidden()
u'<input type="hidden" name="message" value="I love you." />'

For a form with a <select>, use ChoiceField:
>>> class FrameworkForm(Form):
...     name = CharField()
...     language = ChoiceField(choices=[('P', 'Python'), ('J', 'Java')])
>>> f = FrameworkForm(auto_id=False)
>>> print f['language']
<select name="language">
<option value="P">Python</option>
<option value="J">Java</option>
</select>
>>> f = FrameworkForm({'name': 'Django', 'language': 'P'}, auto_id=False)
>>> print f['language']
<select name="language">
<option value="P" selected="selected">Python</option>
<option value="J">Java</option>
</select>

A subtlety: If one of the choices' value is the empty string and the form is
unbound, then the <option> for the empty-string choice will get selected="selected".
>>> class FrameworkForm(Form):
...     name = CharField()
...     language = ChoiceField(choices=[('', '------'), ('P', 'Python'), ('J', 'Java')])
>>> f = FrameworkForm(auto_id=False)
>>> print f['language']
<select name="language">
<option value="" selected="selected">------</option>
<option value="P">Python</option>
<option value="J">Java</option>
</select>

You can specify widget attributes in the Widget constructor.
>>> class FrameworkForm(Form):
...     name = CharField()
...     language = ChoiceField(choices=[('P', 'Python'), ('J', 'Java')], widget=Select(attrs={'class': 'foo'}))
>>> f = FrameworkForm(auto_id=False)
>>> print f['language']
<select class="foo" name="language">
<option value="P">Python</option>
<option value="J">Java</option>
</select>
>>> f = FrameworkForm({'name': 'Django', 'language': 'P'}, auto_id=False)
>>> print f['language']
<select class="foo" name="language">
<option value="P" selected="selected">Python</option>
<option value="J">Java</option>
</select>

When passing a custom widget instance to ChoiceField, note that setting
'choices' on the widget is meaningless. The widget will use the choices
defined on the Field, not the ones defined on the Widget.
>>> class FrameworkForm(Form):
...     name = CharField()
...     language = ChoiceField(choices=[('P', 'Python'), ('J', 'Java')], widget=Select(choices=[('R', 'Ruby'), ('P', 'Perl')], attrs={'class': 'foo'}))
>>> f = FrameworkForm(auto_id=False)
>>> print f['language']
<select class="foo" name="language">
<option value="P">Python</option>
<option value="J">Java</option>
</select>
>>> f = FrameworkForm({'name': 'Django', 'language': 'P'}, auto_id=False)
>>> print f['language']
<select class="foo" name="language">
<option value="P" selected="selected">Python</option>
<option value="J">Java</option>
</select>

You can set a ChoiceField's choices after the fact.
>>> class FrameworkForm(Form):
...     name = CharField()
...     language = ChoiceField()
>>> f = FrameworkForm(auto_id=False)
>>> print f['language']
<select name="language">
</select>
>>> f.fields['language'].choices = [('P', 'Python'), ('J', 'Java')]
>>> print f['language']
<select name="language">
<option value="P">Python</option>
<option value="J">Java</option>
</select>

Add widget=RadioSelect to use that widget with a ChoiceField.
>>> class FrameworkForm(Form):
...     name = CharField()
...     language = ChoiceField(choices=[('P', 'Python'), ('J', 'Java')], widget=RadioSelect)
>>> f = FrameworkForm(auto_id=False)
>>> print f['language']
<ul>
<li><label><input type="radio" name="language" value="P" /> Python</label></li>
<li><label><input type="radio" name="language" value="J" /> Java</label></li>
</ul>
>>> print f
<tr><th>Name:</th><td><input type="text" name="name" /></td></tr>
<tr><th>Language:</th><td><ul>
<li><label><input type="radio" name="language" value="P" /> Python</label></li>
<li><label><input type="radio" name="language" value="J" /> Java</label></li>
</ul></td></tr>
>>> print f.as_ul()
<li>Name: <input type="text" name="name" /></li>
<li>Language: <ul>
<li><label><input type="radio" name="language" value="P" /> Python</label></li>
<li><label><input type="radio" name="language" value="J" /> Java</label></li>
</ul></li>

Regarding auto_id and <label>, RadioSelect is a special case. Each radio button
gets a distinct ID, formed by appending an underscore plus the button's
zero-based index.
>>> f = FrameworkForm(auto_id='id_%s')
>>> print f['language']
<ul>
<li><label><input type="radio" id="id_language_0" value="P" name="language" /> Python</label></li>
<li><label><input type="radio" id="id_language_1" value="J" name="language" /> Java</label></li>
</ul>

When RadioSelect is used with auto_id, and the whole form is printed using
either as_table() or as_ul(), the label for the RadioSelect will point to the
ID of the *first* radio button.
>>> print f
<tr><th><label for="id_name">Name:</label></th><td><input type="text" name="name" id="id_name" /></td></tr>
<tr><th><label for="id_language_0">Language:</label></th><td><ul>
<li><label><input type="radio" id="id_language_0" value="P" name="language" /> Python</label></li>
<li><label><input type="radio" id="id_language_1" value="J" name="language" /> Java</label></li>
</ul></td></tr>
>>> print f.as_ul()
<li><label for="id_name">Name:</label> <input type="text" name="name" id="id_name" /></li>
<li><label for="id_language_0">Language:</label> <ul>
<li><label><input type="radio" id="id_language_0" value="P" name="language" /> Python</label></li>
<li><label><input type="radio" id="id_language_1" value="J" name="language" /> Java</label></li>
</ul></li>
>>> print f.as_p()
<p><label for="id_name">Name:</label> <input type="text" name="name" id="id_name" /></p>
<p><label for="id_language_0">Language:</label> <ul>
<li><label><input type="radio" id="id_language_0" value="P" name="language" /> Python</label></li>
<li><label><input type="radio" id="id_language_1" value="J" name="language" /> Java</label></li>
</ul></p>

MultipleChoiceField is a special case, as its data is required to be a list:
>>> class SongForm(Form):
...     name = CharField()
...     composers = MultipleChoiceField()
>>> f = SongForm(auto_id=False)
>>> print f['composers']
<select multiple="multiple" name="composers">
</select>
>>> class SongForm(Form):
...     name = CharField()
...     composers = MultipleChoiceField(choices=[('J', 'John Lennon'), ('P', 'Paul McCartney')])
>>> f = SongForm(auto_id=False)
>>> print f['composers']
<select multiple="multiple" name="composers">
<option value="J">John Lennon</option>
<option value="P">Paul McCartney</option>
</select>
>>> f = SongForm({'name': 'Yesterday', 'composers': ['P']}, auto_id=False)
>>> print f['name']
<input type="text" name="name" value="Yesterday" />
>>> print f['composers']
<select multiple="multiple" name="composers">
<option value="J">John Lennon</option>
<option value="P" selected="selected">Paul McCartney</option>
</select>

MultipleChoiceField rendered as_hidden() is a special case. Because it can
have multiple values, its as_hidden() renders multiple <input type="hidden">
tags.
>>> f = SongForm({'name': 'Yesterday', 'composers': ['P']}, auto_id=False)
>>> print f['composers'].as_hidden()
<input type="hidden" name="composers" value="P" />
>>> f = SongForm({'name': 'From Me To You', 'composers': ['P', 'J']}, auto_id=False)
>>> print f['composers'].as_hidden()
<input type="hidden" name="composers" value="P" />
<input type="hidden" name="composers" value="J" />

MultipleChoiceField can also be used with the CheckboxSelectMultiple widget.
>>> class SongForm(Form):
...     name = CharField()
...     composers = MultipleChoiceField(choices=[('J', 'John Lennon'), ('P', 'Paul McCartney')], widget=CheckboxSelectMultiple)
>>> f = SongForm(auto_id=False)
>>> print f['composers']
<ul>
<li><label><input type="checkbox" name="composers" value="J" /> John Lennon</label></li>
<li><label><input type="checkbox" name="composers" value="P" /> Paul McCartney</label></li>
</ul>
>>> f = SongForm({'composers': ['J']}, auto_id=False)
>>> print f['composers']
<ul>
<li><label><input checked="checked" type="checkbox" name="composers" value="J" /> John Lennon</label></li>
<li><label><input type="checkbox" name="composers" value="P" /> Paul McCartney</label></li>
</ul>
>>> f = SongForm({'composers': ['J', 'P']}, auto_id=False)
>>> print f['composers']
<ul>
<li><label><input checked="checked" type="checkbox" name="composers" value="J" /> John Lennon</label></li>
<li><label><input checked="checked" type="checkbox" name="composers" value="P" /> Paul McCartney</label></li>
</ul>

Regarding auto_id, CheckboxSelectMultiple is a special case. Each checkbox
gets a distinct ID, formed by appending an underscore plus the checkbox's
zero-based index.
>>> f = SongForm(auto_id='%s_id')
>>> print f['composers']
<ul>
<li><label><input type="checkbox" name="composers" value="J" id="composers_id_0" /> John Lennon</label></li>
<li><label><input type="checkbox" name="composers" value="P" id="composers_id_1" /> Paul McCartney</label></li>
</ul>

Data for a MultipleChoiceField should be a list. QueryDict and MultiValueDict
conveniently work with this.
>>> data = {'name': 'Yesterday', 'composers': ['J', 'P']}
>>> f = SongForm(data)
>>> f.errors
{}
>>> from django.http import QueryDict
>>> data = QueryDict('name=Yesterday&composers=J&composers=P')
>>> f = SongForm(data)
>>> f.errors
{}
>>> from django.utils.datastructures import MultiValueDict
>>> data = MultiValueDict(dict(name=['Yesterday'], composers=['J', 'P']))
>>> f = SongForm(data)
>>> f.errors
{}

The MultipleHiddenInput widget renders multiple values as hidden fields.
>>> class SongFormHidden(Form):
...     name = CharField()
...     composers = MultipleChoiceField(choices=[('J', 'John Lennon'), ('P', 'Paul McCartney')], widget=MultipleHiddenInput)
>>> f = SongFormHidden(MultiValueDict(dict(name=['Yesterday'], composers=['J', 'P'])), auto_id=False)
>>> print f.as_ul()
<li>Name: <input type="text" name="name" value="Yesterday" /><input type="hidden" name="composers" value="J" />
<input type="hidden" name="composers" value="P" /></li>

When using CheckboxSelectMultiple, the framework expects a list of input and
returns a list of input.
>>> f = SongForm({'name': 'Yesterday'}, auto_id=False)
>>> f.errors
{'composers': [u'This field is required.']}
>>> f = SongForm({'name': 'Yesterday', 'composers': ['J']}, auto_id=False)
>>> f.errors
{}
>>> f.clean_data
{'composers': [u'J'], 'name': u'Yesterday'}
>>> f = SongForm({'name': 'Yesterday', 'composers': ['J', 'P']}, auto_id=False)
>>> f.errors
{}
>>> f.clean_data
{'composers': [u'J', u'P'], 'name': u'Yesterday'}

Validation errors are HTML-escaped when output as HTML.
>>> class EscapingForm(Form):
...     special_name = CharField()
...     def clean_special_name(self):
...         raise ValidationError("Something's wrong with '%s'" % self.clean_data['special_name'])

>>> f = EscapingForm({'special_name': "Nothing to escape"}, auto_id=False)
>>> print f
<tr><th>Special name:</th><td><ul class="errorlist"><li>Something&#39;s wrong with &#39;Nothing to escape&#39;</li></ul><input type="text" name="special_name" value="Nothing to escape" /></td></tr>
>>> f = EscapingForm({'special_name': "Should escape < & > and <script>alert('xss')</script>"}, auto_id=False)
>>> print f
<tr><th>Special name:</th><td><ul class="errorlist"><li>Something&#39;s wrong with &#39;Should escape &lt; &amp; &gt; and &lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;&#39;</li></ul><input type="text" name="special_name" value="Should escape &lt; &amp; &gt; and &lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" /></td></tr>

# Validating multiple fields in relation to another ###########################

There are a couple of ways to do multiple-field validation. If you want the
validation message to be associated with a particular field, implement the
clean_XXX() method on the Form, where XXX is the field name. As in
Field.clean(), the clean_XXX() method should return the cleaned value. In the
clean_XXX() method, you have access to self.clean_data, which is a dictionary
of all the data that has been cleaned *so far*, in order by the fields,
including the current field (e.g., the field XXX if you're in clean_XXX()).
>>> class UserRegistration(Form):
...    username = CharField(max_length=10)
...    password1 = CharField(widget=PasswordInput)
...    password2 = CharField(widget=PasswordInput)
...    def clean_password2(self):
...        if self.clean_data.get('password1') and self.clean_data.get('password2') and self.clean_data['password1'] != self.clean_data['password2']:
...            raise ValidationError(u'Please make sure your passwords match.')
...        return self.clean_data['password2']
>>> f = UserRegistration(auto_id=False)
>>> f.errors
{}
>>> f = UserRegistration({}, auto_id=False)
>>> f.errors
{'username': [u'This field is required.'], 'password1': [u'This field is required.'], 'password2': [u'This field is required.']}
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'bar'}, auto_id=False)
>>> f.errors
{'password2': [u'Please make sure your passwords match.']}
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'foo'}, auto_id=False)
>>> f.errors
{}
>>> f.clean_data
{'username': u'adrian', 'password1': u'foo', 'password2': u'foo'}

Another way of doing multiple-field validation is by implementing the
Form's clean() method. If you do this, any ValidationError raised by that
method will not be associated with a particular field; it will have a
special-case association with the field named '__all__'.
Note that in Form.clean(), you have access to self.clean_data, a dictionary of
all the fields/values that have *not* raised a ValidationError. Also note
Form.clean() is required to return a dictionary of all clean data.
>>> class UserRegistration(Form):
...    username = CharField(max_length=10)
...    password1 = CharField(widget=PasswordInput)
...    password2 = CharField(widget=PasswordInput)
...    def clean(self):
...        if self.clean_data.get('password1') and self.clean_data.get('password2') and self.clean_data['password1'] != self.clean_data['password2']:
...            raise ValidationError(u'Please make sure your passwords match.')
...        return self.clean_data
>>> f = UserRegistration(auto_id=False)
>>> f.errors
{}
>>> f = UserRegistration({}, auto_id=False)
>>> print f.as_table()
<tr><th>Username:</th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="username" maxlength="10" /></td></tr>
<tr><th>Password1:</th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="password" name="password1" /></td></tr>
<tr><th>Password2:</th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="password" name="password2" /></td></tr>
>>> f.errors
{'username': [u'This field is required.'], 'password1': [u'This field is required.'], 'password2': [u'This field is required.']}
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'bar'}, auto_id=False)
>>> f.errors
{'__all__': [u'Please make sure your passwords match.']}
>>> print f.as_table()
<tr><td colspan="2"><ul class="errorlist"><li>Please make sure your passwords match.</li></ul></td></tr>
<tr><th>Username:</th><td><input type="text" name="username" value="adrian" maxlength="10" /></td></tr>
<tr><th>Password1:</th><td><input type="password" name="password1" value="foo" /></td></tr>
<tr><th>Password2:</th><td><input type="password" name="password2" value="bar" /></td></tr>
>>> print f.as_ul()
<li><ul class="errorlist"><li>Please make sure your passwords match.</li></ul></li>
<li>Username: <input type="text" name="username" value="adrian" maxlength="10" /></li>
<li>Password1: <input type="password" name="password1" value="foo" /></li>
<li>Password2: <input type="password" name="password2" value="bar" /></li>
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'foo'}, auto_id=False)
>>> f.errors
{}
>>> f.clean_data
{'username': u'adrian', 'password1': u'foo', 'password2': u'foo'}

# Dynamic construction ########################################################

It's possible to construct a Form dynamically by adding to the self.fields
dictionary in __init__(). Don't forget to call Form.__init__() within the
subclass' __init__().
>>> class Person(Form):
...     first_name = CharField()
...     last_name = CharField()
...     def __init__(self, *args, **kwargs):
...         super(Person, self).__init__(*args, **kwargs)
...         self.fields['birthday'] = DateField()
>>> p = Person(auto_id=False)
>>> print p
<tr><th>First name:</th><td><input type="text" name="first_name" /></td></tr>
<tr><th>Last name:</th><td><input type="text" name="last_name" /></td></tr>
<tr><th>Birthday:</th><td><input type="text" name="birthday" /></td></tr>

Instances of a dynamic Form do not persist fields from one Form instance to
the next.
>>> class MyForm(Form):
...     def __init__(self, data=None, auto_id=False, field_list=[]):
...         Form.__init__(self, data, auto_id)
...         for field in field_list:
...             self.fields[field[0]] = field[1]
>>> field_list = [('field1', CharField()), ('field2', CharField())]
>>> my_form = MyForm(field_list=field_list)
>>> print my_form
<tr><th>Field1:</th><td><input type="text" name="field1" /></td></tr>
<tr><th>Field2:</th><td><input type="text" name="field2" /></td></tr>
>>> field_list = [('field3', CharField()), ('field4', CharField())]
>>> my_form = MyForm(field_list=field_list)
>>> print my_form
<tr><th>Field3:</th><td><input type="text" name="field3" /></td></tr>
<tr><th>Field4:</th><td><input type="text" name="field4" /></td></tr>

>>> class MyForm(Form):
...     default_field_1 = CharField()
...     default_field_2 = CharField()
...     def __init__(self, data=None, auto_id=False, field_list=[]):
...         Form.__init__(self, data, auto_id)
...         for field in field_list:
...             self.fields[field[0]] = field[1]
>>> field_list = [('field1', CharField()), ('field2', CharField())]
>>> my_form = MyForm(field_list=field_list)
>>> print my_form
<tr><th>Default field 1:</th><td><input type="text" name="default_field_1" /></td></tr>
<tr><th>Default field 2:</th><td><input type="text" name="default_field_2" /></td></tr>
<tr><th>Field1:</th><td><input type="text" name="field1" /></td></tr>
<tr><th>Field2:</th><td><input type="text" name="field2" /></td></tr>
>>> field_list = [('field3', CharField()), ('field4', CharField())]
>>> my_form = MyForm(field_list=field_list)
>>> print my_form
<tr><th>Default field 1:</th><td><input type="text" name="default_field_1" /></td></tr>
<tr><th>Default field 2:</th><td><input type="text" name="default_field_2" /></td></tr>
<tr><th>Field3:</th><td><input type="text" name="field3" /></td></tr>
<tr><th>Field4:</th><td><input type="text" name="field4" /></td></tr>

Similarly, changes to field attributes do not persist from one Form instance
to the next.
>>> class Person(Form):
...     first_name = CharField(required=False)
...     last_name = CharField(required=False)
...     def __init__(self, names_required=False, *args, **kwargs):
...         super(Person, self).__init__(*args, **kwargs)
...         if names_required:
...             self.fields['first_name'].required = True
...             self.fields['last_name'].required = True
>>> f = Person(names_required=False)
>>> f['first_name'].field.required, f['last_name'].field.required
(False, False)
>>> f = Person(names_required=True)
>>> f['first_name'].field.required, f['last_name'].field.required
(True, True)
>>> f = Person(names_required=False)
>>> f['first_name'].field.required, f['last_name'].field.required
(False, False)
>>> class Person(Form):
...     first_name = CharField(max_length=30)
...     last_name = CharField(max_length=30)
...     def __init__(self, name_max_length=None, *args, **kwargs):
...         super(Person, self).__init__(*args, **kwargs)
...         if name_max_length:
...             self.fields['first_name'].max_length = name_max_length
...             self.fields['last_name'].max_length = name_max_length
>>> f = Person(name_max_length=None)
>>> f['first_name'].field.max_length, f['last_name'].field.max_length
(30, 30)
>>> f = Person(name_max_length=20)
>>> f['first_name'].field.max_length, f['last_name'].field.max_length
(20, 20)
>>> f = Person(name_max_length=None)
>>> f['first_name'].field.max_length, f['last_name'].field.max_length
(30, 30)

HiddenInput widgets are displayed differently in the as_table(), as_ul()
and as_p() output of a Form -- their verbose names are not displayed, and a
separate row is not displayed. They're displayed in the last row of the
form, directly after that row's form element.
>>> class Person(Form):
...     first_name = CharField()
...     last_name = CharField()
...     hidden_text = CharField(widget=HiddenInput)
...     birthday = DateField()
>>> p = Person(auto_id=False)
>>> print p
<tr><th>First name:</th><td><input type="text" name="first_name" /></td></tr>
<tr><th>Last name:</th><td><input type="text" name="last_name" /></td></tr>
<tr><th>Birthday:</th><td><input type="text" name="birthday" /><input type="hidden" name="hidden_text" /></td></tr>
>>> print p.as_ul()
<li>First name: <input type="text" name="first_name" /></li>
<li>Last name: <input type="text" name="last_name" /></li>
<li>Birthday: <input type="text" name="birthday" /><input type="hidden" name="hidden_text" /></li>
>>> print p.as_p()
<p>First name: <input type="text" name="first_name" /></p>
<p>Last name: <input type="text" name="last_name" /></p>
<p>Birthday: <input type="text" name="birthday" /><input type="hidden" name="hidden_text" /></p>

With auto_id set, a HiddenInput still gets an ID, but it doesn't get a label.
>>> p = Person(auto_id='id_%s')
>>> print p
<tr><th><label for="id_first_name">First name:</label></th><td><input type="text" name="first_name" id="id_first_name" /></td></tr>
<tr><th><label for="id_last_name">Last name:</label></th><td><input type="text" name="last_name" id="id_last_name" /></td></tr>
<tr><th><label for="id_birthday">Birthday:</label></th><td><input type="text" name="birthday" id="id_birthday" /><input type="hidden" name="hidden_text" id="id_hidden_text" /></td></tr>
>>> print p.as_ul()
<li><label for="id_first_name">First name:</label> <input type="text" name="first_name" id="id_first_name" /></li>
<li><label for="id_last_name">Last name:</label> <input type="text" name="last_name" id="id_last_name" /></li>
<li><label for="id_birthday">Birthday:</label> <input type="text" name="birthday" id="id_birthday" /><input type="hidden" name="hidden_text" id="id_hidden_text" /></li>
>>> print p.as_p()
<p><label for="id_first_name">First name:</label> <input type="text" name="first_name" id="id_first_name" /></p>
<p><label for="id_last_name">Last name:</label> <input type="text" name="last_name" id="id_last_name" /></p>
<p><label for="id_birthday">Birthday:</label> <input type="text" name="birthday" id="id_birthday" /><input type="hidden" name="hidden_text" id="id_hidden_text" /></p>

If a field with a HiddenInput has errors, the as_table() and as_ul() output
will include the error message(s) with the text "(Hidden field [fieldname]) "
prepended. This message is displayed at the top of the output, regardless of
its field's order in the form.
>>> p = Person({'first_name': 'John', 'last_name': 'Lennon', 'birthday': '1940-10-9'}, auto_id=False)
>>> print p
<tr><td colspan="2"><ul class="errorlist"><li>(Hidden field hidden_text) This field is required.</li></ul></td></tr>
<tr><th>First name:</th><td><input type="text" name="first_name" value="John" /></td></tr>
<tr><th>Last name:</th><td><input type="text" name="last_name" value="Lennon" /></td></tr>
<tr><th>Birthday:</th><td><input type="text" name="birthday" value="1940-10-9" /><input type="hidden" name="hidden_text" /></td></tr>
>>> print p.as_ul()
<li><ul class="errorlist"><li>(Hidden field hidden_text) This field is required.</li></ul></li>
<li>First name: <input type="text" name="first_name" value="John" /></li>
<li>Last name: <input type="text" name="last_name" value="Lennon" /></li>
<li>Birthday: <input type="text" name="birthday" value="1940-10-9" /><input type="hidden" name="hidden_text" /></li>
>>> print p.as_p()
<p><ul class="errorlist"><li>(Hidden field hidden_text) This field is required.</li></ul></p>
<p>First name: <input type="text" name="first_name" value="John" /></p>
<p>Last name: <input type="text" name="last_name" value="Lennon" /></p>
<p>Birthday: <input type="text" name="birthday" value="1940-10-9" /><input type="hidden" name="hidden_text" /></p>

A corner case: It's possible for a form to have only HiddenInputs.
>>> class TestForm(Form):
...     foo = CharField(widget=HiddenInput)
...     bar = CharField(widget=HiddenInput)
>>> p = TestForm(auto_id=False)
>>> print p.as_table()
<input type="hidden" name="foo" /><input type="hidden" name="bar" />
>>> print p.as_ul()
<input type="hidden" name="foo" /><input type="hidden" name="bar" />
>>> print p.as_p()
<input type="hidden" name="foo" /><input type="hidden" name="bar" />

A Form's fields are displayed in the same order in which they were defined.
>>> class TestForm(Form):
...     field1 = CharField()
...     field2 = CharField()
...     field3 = CharField()
...     field4 = CharField()
...     field5 = CharField()
...     field6 = CharField()
...     field7 = CharField()
...     field8 = CharField()
...     field9 = CharField()
...     field10 = CharField()
...     field11 = CharField()
...     field12 = CharField()
...     field13 = CharField()
...     field14 = CharField()
>>> p = TestForm(auto_id=False)
>>> print p
<tr><th>Field1:</th><td><input type="text" name="field1" /></td></tr>
<tr><th>Field2:</th><td><input type="text" name="field2" /></td></tr>
<tr><th>Field3:</th><td><input type="text" name="field3" /></td></tr>
<tr><th>Field4:</th><td><input type="text" name="field4" /></td></tr>
<tr><th>Field5:</th><td><input type="text" name="field5" /></td></tr>
<tr><th>Field6:</th><td><input type="text" name="field6" /></td></tr>
<tr><th>Field7:</th><td><input type="text" name="field7" /></td></tr>
<tr><th>Field8:</th><td><input type="text" name="field8" /></td></tr>
<tr><th>Field9:</th><td><input type="text" name="field9" /></td></tr>
<tr><th>Field10:</th><td><input type="text" name="field10" /></td></tr>
<tr><th>Field11:</th><td><input type="text" name="field11" /></td></tr>
<tr><th>Field12:</th><td><input type="text" name="field12" /></td></tr>
<tr><th>Field13:</th><td><input type="text" name="field13" /></td></tr>
<tr><th>Field14:</th><td><input type="text" name="field14" /></td></tr>

Some Field classes have an effect on the HTML attributes of their associated
Widget. If you set max_length in a CharField and its associated widget is
either a TextInput or PasswordInput, then the widget's rendered HTML will
include the "maxlength" attribute.
>>> class UserRegistration(Form):
...    username = CharField(max_length=10)                   # uses TextInput by default
...    password = CharField(max_length=10, widget=PasswordInput)
...    realname = CharField(max_length=10, widget=TextInput) # redundantly define widget, just to test
...    address = CharField()                                 # no max_length defined here
>>> p = UserRegistration(auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" maxlength="10" /></li>
<li>Password: <input type="password" name="password" maxlength="10" /></li>
<li>Realname: <input type="text" name="realname" maxlength="10" /></li>
<li>Address: <input type="text" name="address" /></li>

If you specify a custom "attrs" that includes the "maxlength" attribute,
the Field's max_length attribute will override whatever "maxlength" you specify
in "attrs".
>>> class UserRegistration(Form):
...    username = CharField(max_length=10, widget=TextInput(attrs={'maxlength': 20}))
...    password = CharField(max_length=10, widget=PasswordInput)
>>> p = UserRegistration(auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" maxlength="10" /></li>
<li>Password: <input type="password" name="password" maxlength="10" /></li>

# Specifying labels ###########################################################

You can specify the label for a field by using the 'label' argument to a Field
class. If you don't specify 'label', Django will use the field name with
underscores converted to spaces, and the initial letter capitalized.
>>> class UserRegistration(Form):
...    username = CharField(max_length=10, label='Your username')
...    password1 = CharField(widget=PasswordInput)
...    password2 = CharField(widget=PasswordInput, label='Password (again)')
>>> p = UserRegistration(auto_id=False)
>>> print p.as_ul()
<li>Your username: <input type="text" name="username" maxlength="10" /></li>
<li>Password1: <input type="password" name="password1" /></li>
<li>Password (again): <input type="password" name="password2" /></li>

A label can be a Unicode object or a bytestring with special characters.
>>> class UserRegistration(Form):
...    username = CharField(max_length=10, label='ŠĐĆŽćžšđ')
...    password = CharField(widget=PasswordInput, label=u'\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111')
>>> p = UserRegistration(auto_id=False)
>>> p.as_ul()
u'<li>\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111: <input type="text" name="username" maxlength="10" /></li>\n<li>\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111: <input type="password" name="password" /></li>'

If a label is set to the empty string for a field, that field won't get a label.
>>> class UserRegistration(Form):
...    username = CharField(max_length=10, label='')
...    password = CharField(widget=PasswordInput)
>>> p = UserRegistration(auto_id=False)
>>> print p.as_ul()
<li> <input type="text" name="username" maxlength="10" /></li>
<li>Password: <input type="password" name="password" /></li>
>>> p = UserRegistration(auto_id='id_%s')
>>> print p.as_ul()
<li> <input id="id_username" type="text" name="username" maxlength="10" /></li>
<li><label for="id_password">Password:</label> <input type="password" name="password" id="id_password" /></li>

If label is None, Django will auto-create the label from the field name. This
is default behavior.
>>> class UserRegistration(Form):
...    username = CharField(max_length=10, label=None)
...    password = CharField(widget=PasswordInput)
>>> p = UserRegistration(auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" maxlength="10" /></li>
<li>Password: <input type="password" name="password" /></li>
>>> p = UserRegistration(auto_id='id_%s')
>>> print p.as_ul()
<li><label for="id_username">Username:</label> <input id="id_username" type="text" name="username" maxlength="10" /></li>
<li><label for="id_password">Password:</label> <input type="password" name="password" id="id_password" /></li>

# Initial data ################################################################

You can specify initial data for a field by using the 'initial' argument to a
Field class. This initial data is displayed when a Form is rendered with *no*
data. It is not displayed when a Form is rendered with any data (including an
empty dictionary). Also, the initial value is *not* used if data for a
particular required field isn't provided.
>>> class UserRegistration(Form):
...    username = CharField(max_length=10, initial='django')
...    password = CharField(widget=PasswordInput)

Here, we're not submitting any data, so the initial value will be displayed.
>>> p = UserRegistration(auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" value="django" maxlength="10" /></li>
<li>Password: <input type="password" name="password" /></li>

Here, we're submitting data, so the initial value will *not* be displayed.
>>> p = UserRegistration({}, auto_id=False)
>>> print p.as_ul()
<li><ul class="errorlist"><li>This field is required.</li></ul>Username: <input type="text" name="username" maxlength="10" /></li>
<li><ul class="errorlist"><li>This field is required.</li></ul>Password: <input type="password" name="password" /></li>
>>> p = UserRegistration({'username': u''}, auto_id=False)
>>> print p.as_ul()
<li><ul class="errorlist"><li>This field is required.</li></ul>Username: <input type="text" name="username" maxlength="10" /></li>
<li><ul class="errorlist"><li>This field is required.</li></ul>Password: <input type="password" name="password" /></li>
>>> p = UserRegistration({'username': u'foo'}, auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" value="foo" maxlength="10" /></li>
<li><ul class="errorlist"><li>This field is required.</li></ul>Password: <input type="password" name="password" /></li>

An 'initial' value is *not* used as a fallback if data is not provided. In this
example, we don't provide a value for 'username', and the form raises a
validation error rather than using the initial value for 'username'.
>>> p = UserRegistration({'password': 'secret'})
>>> p.errors
{'username': [u'This field is required.']}
>>> p.is_valid()
False

# Dynamic initial data ########################################################

The previous technique dealt with "hard-coded" initial data, but it's also
possible to specify initial data after you've already created the Form class
(i.e., at runtime). Use the 'initial' parameter to the Form constructor. This
should be a dictionary containing initial values for one or more fields in the
form, keyed by field name.

>>> class UserRegistration(Form):
...    username = CharField(max_length=10)
...    password = CharField(widget=PasswordInput)

Here, we're not submitting any data, so the initial value will be displayed.
>>> p = UserRegistration(initial={'username': 'django'}, auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" value="django" maxlength="10" /></li>
<li>Password: <input type="password" name="password" /></li>
>>> p = UserRegistration(initial={'username': 'stephane'}, auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" value="stephane" maxlength="10" /></li>
<li>Password: <input type="password" name="password" /></li>

The 'initial' parameter is meaningless if you pass data.
>>> p = UserRegistration({}, initial={'username': 'django'}, auto_id=False)
>>> print p.as_ul()
<li><ul class="errorlist"><li>This field is required.</li></ul>Username: <input type="text" name="username" maxlength="10" /></li>
<li><ul class="errorlist"><li>This field is required.</li></ul>Password: <input type="password" name="password" /></li>
>>> p = UserRegistration({'username': u''}, initial={'username': 'django'}, auto_id=False)
>>> print p.as_ul()
<li><ul class="errorlist"><li>This field is required.</li></ul>Username: <input type="text" name="username" maxlength="10" /></li>
<li><ul class="errorlist"><li>This field is required.</li></ul>Password: <input type="password" name="password" /></li>
>>> p = UserRegistration({'username': u'foo'}, initial={'username': 'django'}, auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" value="foo" maxlength="10" /></li>
<li><ul class="errorlist"><li>This field is required.</li></ul>Password: <input type="password" name="password" /></li>

A dynamic 'initial' value is *not* used as a fallback if data is not provided.
In this example, we don't provide a value for 'username', and the form raises a
validation error rather than using the initial value for 'username'.
>>> p = UserRegistration({'password': 'secret'}, initial={'username': 'django'})
>>> p.errors
{'username': [u'This field is required.']}
>>> p.is_valid()
False

If a Form defines 'initial' *and* 'initial' is passed as a parameter to Form(),
then the latter will get precedence.
>>> class UserRegistration(Form):
...    username = CharField(max_length=10, initial='django')
...    password = CharField(widget=PasswordInput)
>>> p = UserRegistration(initial={'username': 'babik'}, auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" value="babik" maxlength="10" /></li>
<li>Password: <input type="password" name="password" /></li>

# Help text ###################################################################

You can specify descriptive text for a field by using the 'help_text' argument
to a Field class. This help text is displayed when a Form is rendered.
>>> class UserRegistration(Form):
...    username = CharField(max_length=10, help_text='e.g., user@example.com')
...    password = CharField(widget=PasswordInput, help_text='Choose wisely.')
>>> p = UserRegistration(auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" maxlength="10" /> e.g., user@example.com</li>
<li>Password: <input type="password" name="password" /> Choose wisely.</li>
>>> print p.as_p()
<p>Username: <input type="text" name="username" maxlength="10" /> e.g., user@example.com</p>
<p>Password: <input type="password" name="password" /> Choose wisely.</p>
>>> print p.as_table()
<tr><th>Username:</th><td><input type="text" name="username" maxlength="10" /><br />e.g., user@example.com</td></tr>
<tr><th>Password:</th><td><input type="password" name="password" /><br />Choose wisely.</td></tr>

The help text is displayed whether or not data is provided for the form.
>>> p = UserRegistration({'username': u'foo'}, auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" value="foo" maxlength="10" /> e.g., user@example.com</li>
<li><ul class="errorlist"><li>This field is required.</li></ul>Password: <input type="password" name="password" /> Choose wisely.</li>

help_text is not displayed for hidden fields. It can be used for documentation
purposes, though.
>>> class UserRegistration(Form):
...    username = CharField(max_length=10, help_text='e.g., user@example.com')
...    password = CharField(widget=PasswordInput)
...    next = CharField(widget=HiddenInput, initial='/', help_text='Redirect destination')
>>> p = UserRegistration(auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" maxlength="10" /> e.g., user@example.com</li>
<li>Password: <input type="password" name="password" /><input type="hidden" name="next" value="/" /></li>

Help text can include arbitrary Unicode characters.
>>> class UserRegistration(Form):
...    username = CharField(max_length=10, help_text='ŠĐĆŽćžšđ')
>>> p = UserRegistration(auto_id=False)
>>> p.as_ul()
u'<li>Username: <input type="text" name="username" maxlength="10" /> \u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111</li>'

# Subclassing forms ###########################################################

You can subclass a Form to add fields. The resulting form subclass will have
all of the fields of the parent Form, plus whichever fields you define in the
subclass.
>>> class Person(Form):
...     first_name = CharField()
...     last_name = CharField()
...     birthday = DateField()
>>> class Musician(Person):
...     instrument = CharField()
>>> p = Person(auto_id=False)
>>> print p.as_ul()
<li>First name: <input type="text" name="first_name" /></li>
<li>Last name: <input type="text" name="last_name" /></li>
<li>Birthday: <input type="text" name="birthday" /></li>
>>> m = Musician(auto_id=False)
>>> print m.as_ul()
<li>First name: <input type="text" name="first_name" /></li>
<li>Last name: <input type="text" name="last_name" /></li>
<li>Birthday: <input type="text" name="birthday" /></li>
<li>Instrument: <input type="text" name="instrument" /></li>

Yes, you can subclass multiple forms. The fields are added in the order in
which the parent classes are listed.
>>> class Person(Form):
...     first_name = CharField()
...     last_name = CharField()
...     birthday = DateField()
>>> class Instrument(Form):
...     instrument = CharField()
>>> class Beatle(Person, Instrument):
...     haircut_type = CharField()
>>> b = Beatle(auto_id=False)
>>> print b.as_ul()
<li>First name: <input type="text" name="first_name" /></li>
<li>Last name: <input type="text" name="last_name" /></li>
<li>Birthday: <input type="text" name="birthday" /></li>
<li>Instrument: <input type="text" name="instrument" /></li>
<li>Haircut type: <input type="text" name="haircut_type" /></li>

# Forms with prefixes #########################################################

Sometimes it's necessary to have multiple forms display on the same HTML page,
or multiple copies of the same form. We can accomplish this with form prefixes.
Pass the keyword argument 'prefix' to the Form constructor to use this feature.
This value will be prepended to each HTML form field name. One way to think
about this is "namespaces for HTML forms". Notice that in the data argument,
each field's key has the prefix, in this case 'person1', prepended to the
actual field name.
>>> class Person(Form):
...     first_name = CharField()
...     last_name = CharField()
...     birthday = DateField()
>>> data = {
...     'person1-first_name': u'John',
...     'person1-last_name': u'Lennon',
...     'person1-birthday': u'1940-10-9'
... }
>>> p = Person(data, prefix='person1')
>>> print p.as_ul()
<li><label for="id_person1-first_name">First name:</label> <input type="text" name="person1-first_name" value="John" id="id_person1-first_name" /></li>
<li><label for="id_person1-last_name">Last name:</label> <input type="text" name="person1-last_name" value="Lennon" id="id_person1-last_name" /></li>
<li><label for="id_person1-birthday">Birthday:</label> <input type="text" name="person1-birthday" value="1940-10-9" id="id_person1-birthday" /></li>
>>> print p['first_name']
<input type="text" name="person1-first_name" value="John" id="id_person1-first_name" />
>>> print p['last_name']
<input type="text" name="person1-last_name" value="Lennon" id="id_person1-last_name" />
>>> print p['birthday']
<input type="text" name="person1-birthday" value="1940-10-9" id="id_person1-birthday" />
>>> p.errors
{}
>>> p.is_valid()
True
>>> p.clean_data
{'first_name': u'John', 'last_name': u'Lennon', 'birthday': datetime.date(1940, 10, 9)}

Let's try submitting some bad data to make sure form.errors and field.errors
work as expected.
>>> data = {
...     'person1-first_name': u'',
...     'person1-last_name': u'',
...     'person1-birthday': u''
... }
>>> p = Person(data, prefix='person1')
>>> p.errors
{'first_name': [u'This field is required.'], 'last_name': [u'This field is required.'], 'birthday': [u'This field is required.']}
>>> p['first_name'].errors
[u'This field is required.']
>>> p['person1-first_name'].errors
Traceback (most recent call last):
...
KeyError: "Key 'person1-first_name' not found in Form"

In this example, the data doesn't have a prefix, but the form requires it, so
the form doesn't "see" the fields.
>>> data = {
...     'first_name': u'John',
...     'last_name': u'Lennon',
...     'birthday': u'1940-10-9'
... }
>>> p = Person(data, prefix='person1')
>>> p.errors
{'first_name': [u'This field is required.'], 'last_name': [u'This field is required.'], 'birthday': [u'This field is required.']}

With prefixes, a single data dictionary can hold data for multiple instances
of the same form.
>>> data = {
...     'person1-first_name': u'John',
...     'person1-last_name': u'Lennon',
...     'person1-birthday': u'1940-10-9',
...     'person2-first_name': u'Jim',
...     'person2-last_name': u'Morrison',
...     'person2-birthday': u'1943-12-8'
... }
>>> p1 = Person(data, prefix='person1')
>>> p1.is_valid()
True
>>> p1.clean_data
{'first_name': u'John', 'last_name': u'Lennon', 'birthday': datetime.date(1940, 10, 9)}
>>> p2 = Person(data, prefix='person2')
>>> p2.is_valid()
True
>>> p2.clean_data
{'first_name': u'Jim', 'last_name': u'Morrison', 'birthday': datetime.date(1943, 12, 8)}

By default, forms append a hyphen between the prefix and the field name, but a
form can alter that behavior by implementing the add_prefix() method. This
method takes a field name and returns the prefixed field, according to
self.prefix.
>>> class Person(Form):
...     first_name = CharField()
...     last_name = CharField()
...     birthday = DateField()
...     def add_prefix(self, field_name):
...         return self.prefix and '%s-prefix-%s' % (self.prefix, field_name) or field_name
>>> p = Person(prefix='foo')
>>> print p.as_ul()
<li><label for="id_foo-prefix-first_name">First name:</label> <input type="text" name="foo-prefix-first_name" id="id_foo-prefix-first_name" /></li>
<li><label for="id_foo-prefix-last_name">Last name:</label> <input type="text" name="foo-prefix-last_name" id="id_foo-prefix-last_name" /></li>
<li><label for="id_foo-prefix-birthday">Birthday:</label> <input type="text" name="foo-prefix-birthday" id="id_foo-prefix-birthday" /></li>
>>> data = {
...     'foo-prefix-first_name': u'John',
...     'foo-prefix-last_name': u'Lennon',
...     'foo-prefix-birthday': u'1940-10-9'
... }
>>> p = Person(data, prefix='foo')
>>> p.is_valid()
True
>>> p.clean_data
{'first_name': u'John', 'last_name': u'Lennon', 'birthday': datetime.date(1940, 10, 9)}

# Forms with NullBooleanFields ################################################

NullBooleanField is a bit of a special case because its presentation (widget)
is different than its data. This is handled transparently, though.

>>> class Person(Form):
...     name = CharField()
...     is_cool = NullBooleanField()
>>> p = Person({'name': u'Joe'}, auto_id=False)
>>> print p['is_cool']
<select name="is_cool">
<option value="1" selected="selected">Unknown</option>
<option value="2">Yes</option>
<option value="3">No</option>
</select>
>>> p = Person({'name': u'Joe', 'is_cool': u'1'}, auto_id=False)
>>> print p['is_cool']
<select name="is_cool">
<option value="1" selected="selected">Unknown</option>
<option value="2">Yes</option>
<option value="3">No</option>
</select>
>>> p = Person({'name': u'Joe', 'is_cool': u'2'}, auto_id=False)
>>> print p['is_cool']
<select name="is_cool">
<option value="1">Unknown</option>
<option value="2" selected="selected">Yes</option>
<option value="3">No</option>
</select>
>>> p = Person({'name': u'Joe', 'is_cool': u'3'}, auto_id=False)
>>> print p['is_cool']
<select name="is_cool">
<option value="1">Unknown</option>
<option value="2">Yes</option>
<option value="3" selected="selected">No</option>
</select>
>>> p = Person({'name': u'Joe', 'is_cool': True}, auto_id=False)
>>> print p['is_cool']
<select name="is_cool">
<option value="1">Unknown</option>
<option value="2" selected="selected">Yes</option>
<option value="3">No</option>
</select>
>>> p = Person({'name': u'Joe', 'is_cool': False}, auto_id=False)
>>> print p['is_cool']
<select name="is_cool">
<option value="1">Unknown</option>
<option value="2">Yes</option>
<option value="3" selected="selected">No</option>
</select>

# Basic form processing in a view #############################################

>>> from django.template import Template, Context
>>> class UserRegistration(Form):
...    username = CharField(max_length=10)
...    password1 = CharField(widget=PasswordInput)
...    password2 = CharField(widget=PasswordInput)
...    def clean(self):
...        if self.clean_data.get('password1') and self.clean_data.get('password2') and self.clean_data['password1'] != self.clean_data['password2']:
...            raise ValidationError(u'Please make sure your passwords match.')
...        return self.clean_data
>>> def my_function(method, post_data):
...     if method == 'POST':
...         form = UserRegistration(post_data, auto_id=False)
...     else:
...         form = UserRegistration(auto_id=False)
...     if form.is_valid():
...         return 'VALID: %r' % form.clean_data
...     t = Template('<form action="" method="post">\n<table>\n{{ form }}\n</table>\n<input type="submit" />\n</form>')
...     return t.render(Context({'form': form}))

Case 1: GET (an empty form, with no errors).
>>> print my_function('GET', {})
<form action="" method="post">
<table>
<tr><th>Username:</th><td><input type="text" name="username" maxlength="10" /></td></tr>
<tr><th>Password1:</th><td><input type="password" name="password1" /></td></tr>
<tr><th>Password2:</th><td><input type="password" name="password2" /></td></tr>
</table>
<input type="submit" />
</form>

Case 2: POST with erroneous data (a redisplayed form, with errors).
>>> print my_function('POST', {'username': 'this-is-a-long-username', 'password1': 'foo', 'password2': 'bar'})
<form action="" method="post">
<table>
<tr><td colspan="2"><ul class="errorlist"><li>Please make sure your passwords match.</li></ul></td></tr>
<tr><th>Username:</th><td><ul class="errorlist"><li>Ensure this value has at most 10 characters.</li></ul><input type="text" name="username" value="this-is-a-long-username" maxlength="10" /></td></tr>
<tr><th>Password1:</th><td><input type="password" name="password1" value="foo" /></td></tr>
<tr><th>Password2:</th><td><input type="password" name="password2" value="bar" /></td></tr>
</table>
<input type="submit" />
</form>

Case 3: POST with valid data (the success message).
>>> print my_function('POST', {'username': 'adrian', 'password1': 'secret', 'password2': 'secret'})
VALID: {'username': u'adrian', 'password1': u'secret', 'password2': u'secret'}

# Some ideas for using templates with forms ###################################

>>> class UserRegistration(Form):
...    username = CharField(max_length=10, help_text="Good luck picking a username that doesn't already exist.")
...    password1 = CharField(widget=PasswordInput)
...    password2 = CharField(widget=PasswordInput)
...    def clean(self):
...        if self.clean_data.get('password1') and self.clean_data.get('password2') and self.clean_data['password1'] != self.clean_data['password2']:
...            raise ValidationError(u'Please make sure your passwords match.')
...        return self.clean_data

You have full flexibility in displaying form fields in a template. Just pass a
Form instance to the template, and use "dot" access to refer to individual
fields. Note, however, that this flexibility comes with the responsibility of
displaying all the errors, including any that might not be associated with a
particular field.
>>> t = Template('''<form action="">
... {{ form.username.errors.as_ul }}<p><label>Your username: {{ form.username }}</label></p>
... {{ form.password1.errors.as_ul }}<p><label>Password: {{ form.password1 }}</label></p>
... {{ form.password2.errors.as_ul }}<p><label>Password (again): {{ form.password2 }}</label></p>
... <input type="submit" />
... </form>''')
>>> print t.render(Context({'form': UserRegistration(auto_id=False)}))
<form action="">
<p><label>Your username: <input type="text" name="username" maxlength="10" /></label></p>
<p><label>Password: <input type="password" name="password1" /></label></p>
<p><label>Password (again): <input type="password" name="password2" /></label></p>
<input type="submit" />
</form>
>>> print t.render(Context({'form': UserRegistration({'username': 'django'}, auto_id=False)}))
<form action="">
<p><label>Your username: <input type="text" name="username" value="django" maxlength="10" /></label></p>
<ul class="errorlist"><li>This field is required.</li></ul><p><label>Password: <input type="password" name="password1" /></label></p>
<ul class="errorlist"><li>This field is required.</li></ul><p><label>Password (again): <input type="password" name="password2" /></label></p>
<input type="submit" />
</form>

Use form.[field].label to output a field's label. You can specify the label for
a field by using the 'label' argument to a Field class. If you don't specify
'label', Django will use the field name with underscores converted to spaces,
and the initial letter capitalized.
>>> t = Template('''<form action="">
... <p><label>{{ form.username.label }}: {{ form.username }}</label></p>
... <p><label>{{ form.password1.label }}: {{ form.password1 }}</label></p>
... <p><label>{{ form.password2.label }}: {{ form.password2 }}</label></p>
... <input type="submit" />
... </form>''')
>>> print t.render(Context({'form': UserRegistration(auto_id=False)}))
<form action="">
<p><label>Username: <input type="text" name="username" maxlength="10" /></label></p>
<p><label>Password1: <input type="password" name="password1" /></label></p>
<p><label>Password2: <input type="password" name="password2" /></label></p>
<input type="submit" />
</form>

User form.[field].label_tag to output a field's label with a <label> tag
wrapped around it, but *only* if the given field has an "id" attribute.
Recall from above that passing the "auto_id" argument to a Form gives each
field an "id" attribute.
>>> t = Template('''<form action="">
... <p>{{ form.username.label_tag }}: {{ form.username }}</p>
... <p>{{ form.password1.label_tag }}: {{ form.password1 }}</p>
... <p>{{ form.password2.label_tag }}: {{ form.password2 }}</p>
... <input type="submit" />
... </form>''')
>>> print t.render(Context({'form': UserRegistration(auto_id=False)}))
<form action="">
<p>Username: <input type="text" name="username" maxlength="10" /></p>
<p>Password1: <input type="password" name="password1" /></p>
<p>Password2: <input type="password" name="password2" /></p>
<input type="submit" />
</form>
>>> print t.render(Context({'form': UserRegistration(auto_id='id_%s')}))
<form action="">
<p><label for="id_username">Username</label>: <input id="id_username" type="text" name="username" maxlength="10" /></p>
<p><label for="id_password1">Password1</label>: <input type="password" name="password1" id="id_password1" /></p>
<p><label for="id_password2">Password2</label>: <input type="password" name="password2" id="id_password2" /></p>
<input type="submit" />
</form>

User form.[field].help_text to output a field's help text. If the given field
does not have help text, nothing will be output.
>>> t = Template('''<form action="">
... <p>{{ form.username.label_tag }}: {{ form.username }}<br />{{ form.username.help_text }}</p>
... <p>{{ form.password1.label_tag }}: {{ form.password1 }}</p>
... <p>{{ form.password2.label_tag }}: {{ form.password2 }}</p>
... <input type="submit" />
... </form>''')
>>> print t.render(Context({'form': UserRegistration(auto_id=False)}))
<form action="">
<p>Username: <input type="text" name="username" maxlength="10" /><br />Good luck picking a username that doesn't already exist.</p>
<p>Password1: <input type="password" name="password1" /></p>
<p>Password2: <input type="password" name="password2" /></p>
<input type="submit" />
</form>
>>> Template('{{ form.password1.help_text }}').render(Context({'form': UserRegistration(auto_id=False)}))
''

The label_tag() method takes an optional attrs argument: a dictionary of HTML
attributes to add to the <label> tag.
>>> f = UserRegistration(auto_id='id_%s')
>>> for bf in f:
...     print bf.label_tag(attrs={'class': 'pretty'})
<label for="id_username" class="pretty">Username</label>
<label for="id_password1" class="pretty">Password1</label>
<label for="id_password2" class="pretty">Password2</label>

To display the errors that aren't associated with a particular field -- e.g.,
the errors caused by Form.clean() -- use {{ form.non_field_errors }} in the
template. If used on its own, it is displayed as a <ul> (or an empty string, if
the list of errors is empty). You can also use it in {% if %} statements.
>>> t = Template('''<form action="">
... {{ form.username.errors.as_ul }}<p><label>Your username: {{ form.username }}</label></p>
... {{ form.password1.errors.as_ul }}<p><label>Password: {{ form.password1 }}</label></p>
... {{ form.password2.errors.as_ul }}<p><label>Password (again): {{ form.password2 }}</label></p>
... <input type="submit" />
... </form>''')
>>> print t.render(Context({'form': UserRegistration({'username': 'django', 'password1': 'foo', 'password2': 'bar'}, auto_id=False)}))
<form action="">
<p><label>Your username: <input type="text" name="username" value="django" maxlength="10" /></label></p>
<p><label>Password: <input type="password" name="password1" value="foo" /></label></p>
<p><label>Password (again): <input type="password" name="password2" value="bar" /></label></p>
<input type="submit" />
</form>
>>> t = Template('''<form action="">
... {{ form.non_field_errors }}
... {{ form.username.errors.as_ul }}<p><label>Your username: {{ form.username }}</label></p>
... {{ form.password1.errors.as_ul }}<p><label>Password: {{ form.password1 }}</label></p>
... {{ form.password2.errors.as_ul }}<p><label>Password (again): {{ form.password2 }}</label></p>
... <input type="submit" />
... </form>''')
>>> print t.render(Context({'form': UserRegistration({'username': 'django', 'password1': 'foo', 'password2': 'bar'}, auto_id=False)}))
<form action="">
<ul class="errorlist"><li>Please make sure your passwords match.</li></ul>
<p><label>Your username: <input type="text" name="username" value="django" maxlength="10" /></label></p>
<p><label>Password: <input type="password" name="password1" value="foo" /></label></p>
<p><label>Password (again): <input type="password" name="password2" value="bar" /></label></p>
<input type="submit" />
</form>

###############
# Extra stuff #
###############

The newforms library comes with some extra, higher-level Field and Widget
classes that demonstrate some of the library's abilities.

# SelectDateWidget ############################################################

>>> from django.newforms.extras import SelectDateWidget
>>> w = SelectDateWidget(years=('2007','2008','2009','2010','2011','2012','2013','2014','2015','2016'))
>>> print w.render('mydate', '')
<select name="mydate_month">
<option value="1">January</option>
<option value="2">February</option>
<option value="3">March</option>
<option value="4">April</option>
<option value="5">May</option>
<option value="6">June</option>
<option value="7">July</option>
<option value="8">August</option>
<option value="9">September</option>
<option value="10">October</option>
<option value="11">November</option>
<option value="12">December</option>
</select>
<select name="mydate_day">
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="4">4</option>
<option value="5">5</option>
<option value="6">6</option>
<option value="7">7</option>
<option value="8">8</option>
<option value="9">9</option>
<option value="10">10</option>
<option value="11">11</option>
<option value="12">12</option>
<option value="13">13</option>
<option value="14">14</option>
<option value="15">15</option>
<option value="16">16</option>
<option value="17">17</option>
<option value="18">18</option>
<option value="19">19</option>
<option value="20">20</option>
<option value="21">21</option>
<option value="22">22</option>
<option value="23">23</option>
<option value="24">24</option>
<option value="25">25</option>
<option value="26">26</option>
<option value="27">27</option>
<option value="28">28</option>
<option value="29">29</option>
<option value="30">30</option>
<option value="31">31</option>
</select>
<select name="mydate_year">
<option value="2007">2007</option>
<option value="2008">2008</option>
<option value="2009">2009</option>
<option value="2010">2010</option>
<option value="2011">2011</option>
<option value="2012">2012</option>
<option value="2013">2013</option>
<option value="2014">2014</option>
<option value="2015">2015</option>
<option value="2016">2016</option>
</select>
>>> w.render('mydate', None) == w.render('mydate', '')
True
>>> print w.render('mydate', '2010-04-15')
<select name="mydate_month">
<option value="1">January</option>
<option value="2">February</option>
<option value="3">March</option>
<option value="4" selected="selected">April</option>
<option value="5">May</option>
<option value="6">June</option>
<option value="7">July</option>
<option value="8">August</option>
<option value="9">September</option>
<option value="10">October</option>
<option value="11">November</option>
<option value="12">December</option>
</select>
<select name="mydate_day">
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="4">4</option>
<option value="5">5</option>
<option value="6">6</option>
<option value="7">7</option>
<option value="8">8</option>
<option value="9">9</option>
<option value="10">10</option>
<option value="11">11</option>
<option value="12">12</option>
<option value="13">13</option>
<option value="14">14</option>
<option value="15" selected="selected">15</option>
<option value="16">16</option>
<option value="17">17</option>
<option value="18">18</option>
<option value="19">19</option>
<option value="20">20</option>
<option value="21">21</option>
<option value="22">22</option>
<option value="23">23</option>
<option value="24">24</option>
<option value="25">25</option>
<option value="26">26</option>
<option value="27">27</option>
<option value="28">28</option>
<option value="29">29</option>
<option value="30">30</option>
<option value="31">31</option>
</select>
<select name="mydate_year">
<option value="2007">2007</option>
<option value="2008">2008</option>
<option value="2009">2009</option>
<option value="2010" selected="selected">2010</option>
<option value="2011">2011</option>
<option value="2012">2012</option>
<option value="2013">2013</option>
<option value="2014">2014</option>
<option value="2015">2015</option>
<option value="2016">2016</option>
</select>

# USZipCodeField ##############################################################

USZipCodeField validates that the data is either a five-digit U.S. zip code or
a zip+4.
>>> from django.contrib.localflavor.usa.forms import USZipCodeField
>>> f = USZipCodeField()
>>> f.clean('60606')
u'60606'
>>> f.clean(60606)
u'60606'
>>> f.clean('04000')
u'04000'
>>> f.clean('4000')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean('60606-1234')
u'60606-1234'
>>> f.clean('6060-1234')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean('60606-')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = USZipCodeField(required=False)
>>> f.clean('60606')
u'60606'
>>> f.clean(60606)
u'60606'
>>> f.clean('04000')
u'04000'
>>> f.clean('4000')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean('60606-1234')
u'60606-1234'
>>> f.clean('6060-1234')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean('60606-')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# USPhoneNumberField ##########################################################

USPhoneNumberField validates that the data is a valid U.S. phone number,
including the area code. It's normalized to XXX-XXX-XXXX format.
>>> from django.contrib.localflavor.usa.forms import USPhoneNumberField
>>> f = USPhoneNumberField()
>>> f.clean('312-555-1212')
u'312-555-1212'
>>> f.clean('3125551212')
u'312-555-1212'
>>> f.clean('312 555-1212')
u'312-555-1212'
>>> f.clean('(312) 555-1212')
u'312-555-1212'
>>> f.clean('312 555 1212')
u'312-555-1212'
>>> f.clean('312.555.1212')
u'312-555-1212'
>>> f.clean('312.555-1212')
u'312-555-1212'
>>> f.clean(' (312) 555.1212 ')
u'312-555-1212'
>>> f.clean('555-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean('312-55-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = USPhoneNumberField(required=False)
>>> f.clean('312-555-1212')
u'312-555-1212'
>>> f.clean('3125551212')
u'312-555-1212'
>>> f.clean('312 555-1212')
u'312-555-1212'
>>> f.clean('(312) 555-1212')
u'312-555-1212'
>>> f.clean('312 555 1212')
u'312-555-1212'
>>> f.clean('312.555.1212')
u'312-555-1212'
>>> f.clean('312.555-1212')
u'312-555-1212'
>>> f.clean(' (312) 555.1212 ')
u'312-555-1212'
>>> f.clean('555-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean('312-55-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# USStateField ################################################################

USStateField validates that the data is either an abbreviation or name of a
U.S. state.
>>> from django.contrib.localflavor.usa.forms import USStateField
>>> f = USStateField()
>>> f.clean('il')
u'IL'
>>> f.clean('IL')
u'IL'
>>> f.clean('illinois')
u'IL'
>>> f.clean('  illinois ')
u'IL'
>>> f.clean(60606)
Traceback (most recent call last):
...
ValidationError: [u'Enter a U.S. state or territory.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = USStateField(required=False)
>>> f.clean('il')
u'IL'
>>> f.clean('IL')
u'IL'
>>> f.clean('illinois')
u'IL'
>>> f.clean('  illinois ')
u'IL'
>>> f.clean(60606)
Traceback (most recent call last):
...
ValidationError: [u'Enter a U.S. state or territory.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# USStateSelect ###############################################################

USStateSelect is a Select widget that uses a list of U.S. states/territories
as its choices.
>>> from django.contrib.localflavor.usa.forms import USStateSelect
>>> w = USStateSelect()
>>> print w.render('state', 'IL')
<select name="state">
<option value="AL">Alabama</option>
<option value="AK">Alaska</option>
<option value="AS">American Samoa</option>
<option value="AZ">Arizona</option>
<option value="AR">Arkansas</option>
<option value="CA">California</option>
<option value="CO">Colorado</option>
<option value="CT">Connecticut</option>
<option value="DE">Deleware</option>
<option value="DC">District of Columbia</option>
<option value="FM">Federated States of Micronesia</option>
<option value="FL">Florida</option>
<option value="GA">Georgia</option>
<option value="GU">Guam</option>
<option value="HI">Hawaii</option>
<option value="ID">Idaho</option>
<option value="IL" selected="selected">Illinois</option>
<option value="IN">Indiana</option>
<option value="IA">Iowa</option>
<option value="KS">Kansas</option>
<option value="KY">Kentucky</option>
<option value="LA">Louisiana</option>
<option value="ME">Maine</option>
<option value="MH">Marshall Islands</option>
<option value="MD">Maryland</option>
<option value="MA">Massachusetts</option>
<option value="MI">Michigan</option>
<option value="MN">Minnesota</option>
<option value="MS">Mississippi</option>
<option value="MO">Missouri</option>
<option value="MT">Montana</option>
<option value="NE">Nebraska</option>
<option value="NV">Nevada</option>
<option value="NH">New Hampshire</option>
<option value="NJ">New Jersey</option>
<option value="NM">New Mexico</option>
<option value="NY">New York</option>
<option value="NC">North Carolina</option>
<option value="ND">North Dakota</option>
<option value="MP">Northern Mariana Islands</option>
<option value="OH">Ohio</option>
<option value="OK">Oklahoma</option>
<option value="OR">Oregon</option>
<option value="PW">Palau</option>
<option value="PA">Pennsylvania</option>
<option value="PR">Puerto Rico</option>
<option value="RI">Rhode Island</option>
<option value="SC">South Carolina</option>
<option value="SD">South Dakota</option>
<option value="TN">Tennessee</option>
<option value="TX">Texas</option>
<option value="UT">Utah</option>
<option value="VT">Vermont</option>
<option value="VI">Virgin Islands</option>
<option value="VA">Virginia</option>
<option value="WA">Washington</option>
<option value="WV">West Virginia</option>
<option value="WI">Wisconsin</option>
<option value="WY">Wyoming</option>
</select>

# UKPostcodeField #############################################################

UKPostcodeField validates that the data is a valid UK postcode.
>>> from django.contrib.localflavor.uk.forms import UKPostcodeField
>>> f = UKPostcodeField()
>>> f.clean('BT32 4PX')
u'BT32 4PX'
>>> f.clean('GIR 0AA')
u'GIR 0AA'
>>> f.clean('BT324PX')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postcode. A space is required between the two postcode parts.']
>>> f.clean('1NV 4L1D')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postcode. A space is required between the two postcode parts.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = UKPostcodeField(required=False)
>>> f.clean('BT32 4PX')
u'BT32 4PX'
>>> f.clean('GIR 0AA')
u'GIR 0AA'
>>> f.clean('1NV 4L1D')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postcode. A space is required between the two postcode parts.']
>>> f.clean('BT324PX')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postcode. A space is required between the two postcode parts.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# FRZipCodeField #############################################################

FRZipCodeField validates that the data is a valid FR zipcode.
>>> from django.contrib.localflavor.fr.forms import FRZipCodeField
>>> f = FRZipCodeField()
>>> f.clean('75001')
u'75001'
>>> f.clean('93200')
u'93200'
>>> f.clean('2A200')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean('980001')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = FRZipCodeField(required=False)
>>> f.clean('75001')
u'75001'
>>> f.clean('93200')
u'93200'
>>> f.clean('2A200')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean('980001')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean(None)
u''
>>> f.clean('')
u''


# FRPhoneNumberField ##########################################################

FRPhoneNumberField validates that the data is a valid french phone number.
It's normalized to 0X XX XX XX XX format. Dots are valid too.
>>> from django.contrib.localflavor.fr.forms import FRPhoneNumberField
>>> f = FRPhoneNumberField()
>>> f.clean('01 55 44 58 64')
u'01 55 44 58 64'
>>> f.clean('0155445864')
u'01 55 44 58 64'
>>> f.clean('01 5544 5864')
u'01 55 44 58 64'
>>> f.clean('01 55.44.58.64')
u'01 55 44 58 64'
>>> f.clean('01.55.44.58.64')
u'01 55 44 58 64'
>>> f.clean('01,55,44,58,64')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in 0X XX XX XX XX format.']
>>> f.clean('555 015 544')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in 0X XX XX XX XX format.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = FRPhoneNumberField(required=False)
>>> f.clean('01 55 44 58 64')
u'01 55 44 58 64'
>>> f.clean('0155445864')
u'01 55 44 58 64'
>>> f.clean('01 5544 5864')
u'01 55 44 58 64'
>>> f.clean('01 55.44.58.64')
u'01 55 44 58 64'
>>> f.clean('01.55.44.58.64')
u'01 55 44 58 64'
>>> f.clean('01,55,44,58,64')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in 0X XX XX XX XX format.']
>>> f.clean('555 015 544')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in 0X XX XX XX XX format.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# FRDepartmentSelect ###############################################################

FRDepartmentSelect is a Select widget that uses a list of french departments 
including DOM TOM
>>> from django.contrib.localflavor.fr.forms import FRDepartmentSelect
>>> w = FRDepartmentSelect()
>>> print w.render('dep', 'Paris')
<select name="dep">
<option value="01">01 - Ain</option>
<option value="02">02 - Aisne</option>
<option value="03">03 - Allier</option>
<option value="04">04 - Alpes-de-Haute-Provence</option>
<option value="05">05 - Hautes-Alpes</option>
<option value="06">06 - Alpes-Maritimes</option>
<option value="07">07 - Ardeche</option>
<option value="08">08 - Ardennes</option>
<option value="09">09 - Ariege</option>
<option value="10">10 - Aube</option>
<option value="11">11 - Aude</option>
<option value="12">12 - Aveyron</option>
<option value="13">13 - Bouches-du-Rhone</option>
<option value="14">14 - Calvados</option>
<option value="15">15 - Cantal</option>
<option value="16">16 - Charente</option>
<option value="17">17 - Charente-Maritime</option>
<option value="18">18 - Cher</option>
<option value="19">19 - Correze</option>
<option value="21">21 - Cote-d&#39;Or</option>
<option value="22">22 - Cotes-d&#39;Armor</option>
<option value="23">23 - Creuse</option>
<option value="24">24 - Dordogne</option>
<option value="25">25 - Doubs</option>
<option value="26">26 - Drome</option>
<option value="27">27 - Eure</option>
<option value="28">28 - Eure-et-Loire</option>
<option value="29">29 - Finistere</option>
<option value="2A">2A - Corse-du-Sud</option>
<option value="2B">2B - Haute-Corse</option>
<option value="30">30 - Gard</option>
<option value="31">31 - Haute-Garonne</option>
<option value="32">32 - Gers</option>
<option value="33">33 - Gironde</option>
<option value="34">34 - Herault</option>
<option value="35">35 - Ille-et-Vilaine</option>
<option value="36">36 - Indre</option>
<option value="37">37 - Indre-et-Loire</option>
<option value="38">38 - Isere</option>
<option value="39">39 - Jura</option>
<option value="40">40 - Landes</option>
<option value="41">41 - Loir-et-Cher</option>
<option value="42">42 - Loire</option>
<option value="43">43 - Haute-Loire</option>
<option value="44">44 - Loire-Atlantique</option>
<option value="45">45 - Loiret</option>
<option value="46">46 - Lot</option>
<option value="47">47 - Lot-et-Garonne</option>
<option value="48">48 - Lozere</option>
<option value="49">49 - Maine-et-Loire</option>
<option value="50">50 - Manche</option>
<option value="51">51 - Marne</option>
<option value="52">52 - Haute-Marne</option>
<option value="53">53 - Mayenne</option>
<option value="54">54 - Meurthe-et-Moselle</option>
<option value="55">55 - Meuse</option>
<option value="56">56 - Morbihan</option>
<option value="57">57 - Moselle</option>
<option value="58">58 - Nievre</option>
<option value="59">59 - Nord</option>
<option value="60">60 - Oise</option>
<option value="61">61 - Orne</option>
<option value="62">62 - Pas-de-Calais</option>
<option value="63">63 - Puy-de-Dome</option>
<option value="64">64 - Pyrenees-Atlantiques</option>
<option value="65">65 - Hautes-Pyrenees</option>
<option value="66">66 - Pyrenees-Orientales</option>
<option value="67">67 - Bas-Rhin</option>
<option value="68">68 - Haut-Rhin</option>
<option value="69">69 - Rhone</option>
<option value="70">70 - Haute-Saone</option>
<option value="71">71 - Saone-et-Loire</option>
<option value="72">72 - Sarthe</option>
<option value="73">73 - Savoie</option>
<option value="74">74 - Haute-Savoie</option>
<option value="75">75 - Paris</option>
<option value="76">76 - Seine-Maritime</option>
<option value="77">77 - Seine-et-Marne</option>
<option value="78">78 - Yvelines</option>
<option value="79">79 - Deux-Sevres</option>
<option value="80">80 - Somme</option>
<option value="81">81 - Tarn</option>
<option value="82">82 - Tarn-et-Garonne</option>
<option value="83">83 - Var</option>
<option value="84">84 - Vaucluse</option>
<option value="85">85 - Vendee</option>
<option value="86">86 - Vienne</option>
<option value="87">87 - Haute-Vienne</option>
<option value="88">88 - Vosges</option>
<option value="89">89 - Yonne</option>
<option value="90">90 - Territoire de Belfort</option>
<option value="91">91 - Essonne</option>
<option value="92">92 - Hauts-de-Seine</option>
<option value="93">93 - Seine-Saint-Denis</option>
<option value="94">94 - Val-de-Marne</option>
<option value="95">95 - Val-d&#39;Oise</option>
<option value="2A">2A - Corse du sud</option>
<option value="2B">2B - Haute Corse</option>
<option value="971">971 - Guadeloupe</option>
<option value="972">972 - Martinique</option>
<option value="973">973 - Guyane</option>
<option value="974">974 - La Reunion</option>
<option value="975">975 - Saint-Pierre-et-Miquelon</option>
<option value="976">976 - Mayotte</option>
<option value="984">984 - Terres Australes et Antarctiques</option>
<option value="986">986 - Wallis et Futuna</option>
<option value="987">987 - Polynesie Francaise</option>
<option value="988">988 - Nouvelle-Caledonie</option>
</select>

# JPPostalCodeField ###############################################################

A form field that validates its input is a Japanese postcode.

Accepts 7 digits(with/out hyphen).
>>> from django.contrib.localflavor.jp.forms import JPPostalCodeField
>>> f = JPPostalCodeField()
>>> f.clean('251-0032')
u'2510032'
>>> f.clean('2510032')
u'2510032'
>>> f.clean('2510-032')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXXXXXX or XXX-XXXX.']
>>> f.clean('251a0032')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXXXXXX or XXX-XXXX.']
>>> f.clean('a51-0032')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXXXXXX or XXX-XXXX.']
>>> f.clean('25100321')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXXXXXX or XXX-XXXX.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = JPPostalCodeField(required=False)
>>> f.clean('251-0032')
u'2510032'
>>> f.clean('2510032')
u'2510032'
>>> f.clean('2510-032')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXXXXXX or XXX-XXXX.']
>>> f.clean('')
u''
>>> f.clean(None)
u''

# JPPrefectureSelect ###############################################################

A Select widget that uses a list of Japanese prefectures as its choices.
>>> from django.contrib.localflavor.jp.forms import JPPrefectureSelect
>>> w = JPPrefectureSelect()
>>> print w.render('prefecture', 'kanagawa')
<select name="prefecture">
<option value="hokkaido">Hokkaido</option>
<option value="aomori">Aomori</option>
<option value="iwate">Iwate</option>
<option value="miyagi">Miyagi</option>
<option value="akita">Akita</option>
<option value="yamagata">Yamagata</option>
<option value="fukushima">Fukushima</option>
<option value="ibaraki">Ibaraki</option>
<option value="tochigi">Tochigi</option>
<option value="gunma">Gunma</option>
<option value="saitama">Saitama</option>
<option value="chiba">Chiba</option>
<option value="tokyo">Tokyo</option>
<option value="kanagawa" selected="selected">Kanagawa</option>
<option value="yamanashi">Yamanashi</option>
<option value="nagano">Nagano</option>
<option value="niigata">Niigata</option>
<option value="toyama">Toyama</option>
<option value="ishikawa">Ishikawa</option>
<option value="fukui">Fukui</option>
<option value="gifu">Gifu</option>
<option value="shizuoka">Shizuoka</option>
<option value="aichi">Aichi</option>
<option value="mie">Mie</option>
<option value="shiga">Shiga</option>
<option value="kyoto">Kyoto</option>
<option value="osaka">Osaka</option>
<option value="hyogo">Hyogo</option>
<option value="nara">Nara</option>
<option value="wakayama">Wakayama</option>
<option value="tottori">Tottori</option>
<option value="shimane">Shimane</option>
<option value="okayama">Okayama</option>
<option value="hiroshima">Hiroshima</option>
<option value="yamaguchi">Yamaguchi</option>
<option value="tokushima">Tokushima</option>
<option value="kagawa">Kagawa</option>
<option value="ehime">Ehime</option>
<option value="kochi">Kochi</option>
<option value="fukuoka">Fukuoka</option>
<option value="saga">Saga</option>
<option value="nagasaki">Nagasaki</option>
<option value="kumamoto">Kumamoto</option>
<option value="oita">Oita</option>
<option value="miyazaki">Miyazaki</option>
<option value="kagoshima">Kagoshima</option>
<option value="okinawa">Okinawa</option>
</select>

# FIZipCodeField #############################################################

FIZipCodeField validates that the data is a valid FI zipcode.
>>> from django.contrib.localflavor.fi.forms import FIZipCodeField
>>> f = FIZipCodeField()
>>> f.clean('20540')
u'20540'
>>> f.clean('20101')
u'20101'
>>> f.clean('20s40')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean('205401')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = FIZipCodeField(required=False)
>>> f.clean('20540')
u'20540'
>>> f.clean('20101')
u'20101'
>>> f.clean('20s40')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean('205401')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# FIMunicipalitySelect ############################################################### 

A Select widget that uses a list of Finnish municipalities as its choices. 
>>> from django.contrib.localflavor.fi.forms import FIMunicipalitySelect 
>>> w = FIMunicipalitySelect() 
>>> unicode(w.render('municipalities', 'turku'))
u'<select name="municipalities">\n<option value="akaa">Akaa</option>\n<option value="alaharma">Alah\xe4rm\xe4</option>\n<option value="alajarvi">Alaj\xe4rvi</option>\n<option value="alastaro">Alastaro</option>\n<option value="alavieska">Alavieska</option>\n<option value="alavus">Alavus</option>\n<option value="anjalankoski">Anjalankoski</option>\n<option value="artjarvi">Artj\xe4rvi</option>\n<option value="asikkala">Asikkala</option>\n<option value="askainen">Askainen</option>\n<option value="askola">Askola</option>\n<option value="aura">Aura</option>\n<option value="brando">Br\xe4nd\xf6</option>\n<option value="dragsfjard">Dragsfj\xe4rd</option>\n<option value="eckero">Ecker\xf6</option>\n<option value="elimaki">Elim\xe4ki</option>\n<option value="eno">Eno</option>\n<option value="enonkoski">Enonkoski</option>\n<option value="enontekio">Enonteki\xf6</option>\n<option value="espoo">Espoo</option>\n<option value="eura">Eura</option>\n<option value="eurajoki">Eurajoki</option>\n<option value="evijarvi">Evij\xe4rvi</option>\n<option value="finstrom">Finstr\xf6m</option>\n<option value="forssa">Forssa</option>\n<option value="foglo">F\xf6gl\xf6</option>\n<option value="geta">Geta</option>\n<option value="haapajarvi">Haapaj\xe4rvi</option>\n<option value="haapavesi">Haapavesi</option>\n<option value="hailuoto">Hailuoto</option>\n<option value="halikko">Halikko</option>\n<option value="halsua">Halsua</option>\n<option value="hamina">Hamina</option>\n<option value="hammarland">Hammarland</option>\n<option value="hankasalmi">Hankasalmi</option>\n<option value="hanko">Hanko</option>\n<option value="harjavalta">Harjavalta</option>\n<option value="hartola">Hartola</option>\n<option value="hattula">Hattula</option>\n<option value="hauho">Hauho</option>\n<option value="haukipudas">Haukipudas</option>\n<option value="hausjarvi">Hausj\xe4rvi</option>\n<option value="heinola">Heinola</option>\n<option value="heinavesi">Hein\xe4vesi</option>\n<option value="helsinki">Helsinki</option>\n<option value="himanka">Himanka</option>\n<option value="hirvensalmi">Hirvensalmi</option>\n<option value="hollola">Hollola</option>\n<option value="honkajoki">Honkajoki</option>\n<option value="houtskari">Houtskari</option>\n<option value="huittinen">Huittinen</option>\n<option value="humppila">Humppila</option>\n<option value="hyrynsalmi">Hyrynsalmi</option>\n<option value="hyvinkaa">Hyvink\xe4\xe4</option>\n<option value="hameenkoski">H\xe4meenkoski</option>\n<option value="hameenkyro">H\xe4meenkyr\xf6</option>\n<option value="hameenlinna">H\xe4meenlinna</option>\n<option value="ii">Ii</option>\n<option value="iisalmi">Iisalmi</option>\n<option value="iitti">Iitti</option>\n<option value="ikaalinen">Ikaalinen</option>\n<option value="ilmajoki">Ilmajoki</option>\n<option value="ilomantsi">Ilomantsi</option>\n<option value="imatra">Imatra</option>\n<option value="inari">Inari</option>\n<option value="inio">Ini\xf6</option>\n<option value="inkoo">Inkoo</option>\n<option value="isojoki">Isojoki</option>\n<option value="isokyro">Isokyr\xf6</option>\n<option value="jaala">Jaala</option>\n<option value="jalasjarvi">Jalasj\xe4rvi</option>\n<option value="janakkala">Janakkala</option>\n<option value="joensuu">Joensuu</option>\n<option value="jokioinen">Jokioinen</option>\n<option value="jomala">Jomala</option>\n<option value="joroinen">Joroinen</option>\n<option value="joutsa">Joutsa</option>\n<option value="joutseno">Joutseno</option>\n<option value="juankoski">Juankoski</option>\n<option value="jurva">Jurva</option>\n<option value="juuka">Juuka</option>\n<option value="juupajoki">Juupajoki</option>\n<option value="juva">Juva</option>\n<option value="jyvaskyla">Jyv\xe4skyl\xe4</option>\n<option value="jyvaskylan_mlk">Jyv\xe4skyl\xe4n maalaiskunta</option>\n<option value="jamijarvi">J\xe4mij\xe4rvi</option>\n<option value="jamsa">J\xe4ms\xe4</option>\n<option value="jamsankoski">J\xe4ms\xe4nkoski</option>\n<option value="jarvenpaa">J\xe4rvenp\xe4\xe4</option>\n<option value="kaarina">Kaarina</option>\n<option value="kaavi">Kaavi</option>\n<option value="kajaani">Kajaani</option>\n<option value="kalajoki">Kalajoki</option>\n<option value="kalvola">Kalvola</option>\n<option value="kangasala">Kangasala</option>\n<option value="kangasniemi">Kangasniemi</option>\n<option value="kankaanpaa">Kankaanp\xe4\xe4</option>\n<option value="kannonkoski">Kannonkoski</option>\n<option value="kannus">Kannus</option>\n<option value="karijoki">Karijoki</option>\n<option value="karjaa">Karjaa</option>\n<option value="karjalohja">Karjalohja</option>\n<option value="karkkila">Karkkila</option>\n<option value="karstula">Karstula</option>\n<option value="karttula">Karttula</option>\n<option value="karvia">Karvia</option>\n<option value="kaskinen">Kaskinen</option>\n<option value="kauhajoki">Kauhajoki</option>\n<option value="kauhava">Kauhava</option>\n<option value="kauniainen">Kauniainen</option>\n<option value="kaustinen">Kaustinen</option>\n<option value="keitele">Keitele</option>\n<option value="kemi">Kemi</option>\n<option value="kemijarvi">Kemij\xe4rvi</option>\n<option value="keminmaa">Keminmaa</option>\n<option value="kemio">Kemi\xf6</option>\n<option value="kempele">Kempele</option>\n<option value="kerava">Kerava</option>\n<option value="kerimaki">Kerim\xe4ki</option>\n<option value="kestila">Kestil\xe4</option>\n<option value="kesalahti">Kes\xe4lahti</option>\n<option value="keuruu">Keuruu</option>\n<option value="kihnio">Kihni\xf6</option>\n<option value="kiikala">Kiikala</option>\n<option value="kiikoinen">Kiikoinen</option>\n<option value="kiiminki">Kiiminki</option>\n<option value="kinnula">Kinnula</option>\n<option value="kirkkonummi">Kirkkonummi</option>\n<option value="kisko">Kisko</option>\n<option value="kitee">Kitee</option>\n<option value="kittila">Kittil\xe4</option>\n<option value="kiukainen">Kiukainen</option>\n<option value="kiuruvesi">Kiuruvesi</option>\n<option value="kivijarvi">Kivij\xe4rvi</option>\n<option value="kokemaki">Kokem\xe4ki</option>\n<option value="kokkola">Kokkola</option>\n<option value="kolari">Kolari</option>\n<option value="konnevesi">Konnevesi</option>\n<option value="kontiolahti">Kontiolahti</option>\n<option value="korpilahti">Korpilahti</option>\n<option value="korppoo">Korppoo</option>\n<option value="korsnas">Korsn\xe4s</option>\n<option value="kortesjarvi">Kortesj\xe4rvi</option>\n<option value="koskitl">KoskiTl</option>\n<option value="kotka">Kotka</option>\n<option value="kouvola">Kouvola</option>\n<option value="kristiinankaupunki">Kristiinankaupunki</option>\n<option value="kruunupyy">Kruunupyy</option>\n<option value="kuhmalahti">Kuhmalahti</option>\n<option value="kuhmo">Kuhmo</option>\n<option value="kuhmoinen">Kuhmoinen</option>\n<option value="kumlinge">Kumlinge</option>\n<option value="kuopio">Kuopio</option>\n<option value="kuortane">Kuortane</option>\n<option value="kurikka">Kurikka</option>\n<option value="kuru">Kuru</option>\n<option value="kustavi">Kustavi</option>\n<option value="kuusamo">Kuusamo</option>\n<option value="kuusankoski">Kuusankoski</option>\n<option value="kuusjoki">Kuusjoki</option>\n<option value="kylmakoski">Kylm\xe4koski</option>\n<option value="kyyjarvi">Kyyj\xe4rvi</option>\n<option value="kalvia">K\xe4lvi\xe4</option>\n<option value="karkola">K\xe4rk\xf6l\xe4</option>\n<option value="karsamaki">K\xe4rs\xe4m\xe4ki</option>\n<option value="kokar">K\xf6kar</option>\n<option value="koylio">K\xf6yli\xf6</option>\n<option value="lahti">Lahti</option>\n<option value="laihia">Laihia</option>\n<option value="laitila">Laitila</option>\n<option value="lammi">Lammi</option>\n<option value="lapinjarvi">Lapinj\xe4rvi</option>\n<option value="lapinlahti">Lapinlahti</option>\n<option value="lappajarvi">Lappaj\xe4rvi</option>\n<option value="lappeenranta">Lappeenranta</option>\n<option value="lappi">Lappi</option>\n<option value="lapua">Lapua</option>\n<option value="laukaa">Laukaa</option>\n<option value="lavia">Lavia</option>\n<option value="lehtimaki">Lehtim\xe4ki</option>\n<option value="leivonmaki">Leivonm\xe4ki</option>\n<option value="lemi">Lemi</option>\n<option value="lemland">Lemland</option>\n<option value="lempaala">Lemp\xe4\xe4l\xe4</option>\n<option value="lemu">Lemu</option>\n<option value="leppavirta">Lepp\xe4virta</option>\n<option value="lestijarvi">Lestij\xe4rvi</option>\n<option value="lieksa">Lieksa</option>\n<option value="lieto">Lieto</option>\n<option value="liljendal">Liljendal</option>\n<option value="liminka">Liminka</option>\n<option value="liperi">Liperi</option>\n<option value="lohja">Lohja</option>\n<option value="lohtaja">Lohtaja</option>\n<option value="loimaa">Loimaa</option>\n<option value="loppi">Loppi</option>\n<option value="loviisa">Loviisa</option>\n<option value="luhanka">Luhanka</option>\n<option value="lumijoki">Lumijoki</option>\n<option value="lumparland">Lumparland</option>\n<option value="luoto">Luoto</option>\n<option value="luumaki">Luum\xe4ki</option>\n<option value="luvia">Luvia</option>\n<option value="maalahti">Maalahti</option>\n<option value="maaninka">Maaninka</option>\n<option value="maarianhamina">Maarianhamina</option>\n<option value="marttila">Marttila</option>\n<option value="masku">Masku</option>\n<option value="mellila">Mellil\xe4</option>\n<option value="merijarvi">Merij\xe4rvi</option>\n<option value="merikarvia">Merikarvia</option>\n<option value="merimasku">Merimasku</option>\n<option value="miehikkala">Miehikk\xe4l\xe4</option>\n<option value="mikkeli">Mikkeli</option>\n<option value="mouhijarvi">Mouhij\xe4rvi</option>\n<option value="muhos">Muhos</option>\n<option value="multia">Multia</option>\n<option value="muonio">Muonio</option>\n<option value="mustasaari">Mustasaari</option>\n<option value="muurame">Muurame</option>\n<option value="muurla">Muurla</option>\n<option value="mynamaki">Myn\xe4m\xe4ki</option>\n<option value="myrskyla">Myrskyl\xe4</option>\n<option value="mantsala">M\xe4nts\xe4l\xe4</option>\n<option value="mantta">M\xe4ntt\xe4</option>\n<option value="mantyharju">M\xe4ntyharju</option>\n<option value="naantali">Naantali</option>\n<option value="nakkila">Nakkila</option>\n<option value="nastola">Nastola</option>\n<option value="nauvo">Nauvo</option>\n<option value="nilsia">Nilsi\xe4</option>\n<option value="nivala">Nivala</option>\n<option value="nokia">Nokia</option>\n<option value="noormarkku">Noormarkku</option>\n<option value="nousiainen">Nousiainen</option>\n<option value="nummi-pusula">Nummi-Pusula</option>\n<option value="nurmes">Nurmes</option>\n<option value="nurmijarvi">Nurmij\xe4rvi</option>\n<option value="nurmo">Nurmo</option>\n<option value="narpio">N\xe4rpi\xf6</option>\n<option value="oravainen">Oravainen</option>\n<option value="orimattila">Orimattila</option>\n<option value="oripaa">Orip\xe4\xe4</option>\n<option value="orivesi">Orivesi</option>\n<option value="oulainen">Oulainen</option>\n<option value="oulu">Oulu</option>\n<option value="oulunsalo">Oulunsalo</option>\n<option value="outokumpu">Outokumpu</option>\n<option value="padasjoki">Padasjoki</option>\n<option value="paimio">Paimio</option>\n<option value="paltamo">Paltamo</option>\n<option value="parainen">Parainen</option>\n<option value="parikkala">Parikkala</option>\n<option value="parkano">Parkano</option>\n<option value="pedersore">Peders\xf6re</option>\n<option value="pelkosenniemi">Pelkosenniemi</option>\n<option value="pello">Pello</option>\n<option value="perho">Perho</option>\n<option value="pernaja">Pernaja</option>\n<option value="pernio">Perni\xf6</option>\n<option value="pertteli">Pertteli</option>\n<option value="pertunmaa">Pertunmaa</option>\n<option value="petajavesi">Pet\xe4j\xe4vesi</option>\n<option value="pieksamaki">Pieks\xe4m\xe4ki</option>\n<option value="pielavesi">Pielavesi</option>\n<option value="pietarsaari">Pietarsaari</option>\n<option value="pihtipudas">Pihtipudas</option>\n<option value="piikkio">Piikki\xf6</option>\n<option value="piippola">Piippola</option>\n<option value="pirkkala">Pirkkala</option>\n<option value="pohja">Pohja</option>\n<option value="polvijarvi">Polvij\xe4rvi</option>\n<option value="pomarkku">Pomarkku</option>\n<option value="pori">Pori</option>\n<option value="pornainen">Pornainen</option>\n<option value="porvoo">Porvoo</option>\n<option value="posio">Posio</option>\n<option value="pudasjarvi">Pudasj\xe4rvi</option>\n<option value="pukkila">Pukkila</option>\n<option value="pulkkila">Pulkkila</option>\n<option value="punkaharju">Punkaharju</option>\n<option value="punkalaidun">Punkalaidun</option>\n<option value="puolanka">Puolanka</option>\n<option value="puumala">Puumala</option>\n<option value="pyhtaa">Pyht\xe4\xe4</option>\n<option value="pyhajoki">Pyh\xe4joki</option>\n<option value="pyhajarvi">Pyh\xe4j\xe4rvi</option>\n<option value="pyhanta">Pyh\xe4nt\xe4</option>\n<option value="pyharanta">Pyh\xe4ranta</option>\n<option value="pyhaselka">Pyh\xe4selk\xe4</option>\n<option value="pylkonmaki">Pylk\xf6nm\xe4ki</option>\n<option value="palkane">P\xe4lk\xe4ne</option>\n<option value="poytya">P\xf6yty\xe4</option>\n<option value="raahe">Raahe</option>\n<option value="raisio">Raisio</option>\n<option value="rantasalmi">Rantasalmi</option>\n<option value="rantsila">Rantsila</option>\n<option value="ranua">Ranua</option>\n<option value="rauma">Rauma</option>\n<option value="rautalampi">Rautalampi</option>\n<option value="rautavaara">Rautavaara</option>\n<option value="rautjarvi">Rautj\xe4rvi</option>\n<option value="reisjarvi">Reisj\xe4rvi</option>\n<option value="renko">Renko</option>\n<option value="riihimaki">Riihim\xe4ki</option>\n<option value="ristiina">Ristiina</option>\n<option value="ristijarvi">Ristij\xe4rvi</option>\n<option value="rovaniemi">Rovaniemi</option>\n<option value="ruokolahti">Ruokolahti</option>\n<option value="ruotsinpyhtaa">Ruotsinpyht\xe4\xe4</option>\n<option value="ruovesi">Ruovesi</option>\n<option value="rusko">Rusko</option>\n<option value="rymattyla">Rym\xe4ttyl\xe4</option>\n<option value="raakkyla">R\xe4\xe4kkyl\xe4</option>\n<option value="saarijarvi">Saarij\xe4rvi</option>\n<option value="salla">Salla</option>\n<option value="salo">Salo</option>\n<option value="saltvik">Saltvik</option>\n<option value="sammatti">Sammatti</option>\n<option value="sauvo">Sauvo</option>\n<option value="savitaipale">Savitaipale</option>\n<option value="savonlinna">Savonlinna</option>\n<option value="savonranta">Savonranta</option>\n<option value="savukoski">Savukoski</option>\n<option value="seinajoki">Sein\xe4joki</option>\n<option value="sievi">Sievi</option>\n<option value="siikainen">Siikainen</option>\n<option value="siikajoki">Siikajoki</option>\n<option value="siilinjarvi">Siilinj\xe4rvi</option>\n<option value="simo">Simo</option>\n<option value="sipoo">Sipoo</option>\n<option value="siuntio">Siuntio</option>\n<option value="sodankyla">Sodankyl\xe4</option>\n<option value="soini">Soini</option>\n<option value="somero">Somero</option>\n<option value="sonkajarvi">Sonkaj\xe4rvi</option>\n<option value="sotkamo">Sotkamo</option>\n<option value="sottunga">Sottunga</option>\n<option value="sulkava">Sulkava</option>\n<option value="sund">Sund</option>\n<option value="suomenniemi">Suomenniemi</option>\n<option value="suomusjarvi">Suomusj\xe4rvi</option>\n<option value="suomussalmi">Suomussalmi</option>\n<option value="suonenjoki">Suonenjoki</option>\n<option value="sysma">Sysm\xe4</option>\n<option value="sakyla">S\xe4kyl\xe4</option>\n<option value="sarkisalo">S\xe4rkisalo</option>\n<option value="taipalsaari">Taipalsaari</option>\n<option value="taivalkoski">Taivalkoski</option>\n<option value="taivassalo">Taivassalo</option>\n<option value="tammela">Tammela</option>\n<option value="tammisaari">Tammisaari</option>\n<option value="tampere">Tampere</option>\n<option value="tarvasjoki">Tarvasjoki</option>\n<option value="tervo">Tervo</option>\n<option value="tervola">Tervola</option>\n<option value="teuva">Teuva</option>\n<option value="tohmajarvi">Tohmaj\xe4rvi</option>\n<option value="toholampi">Toholampi</option>\n<option value="toivakka">Toivakka</option>\n<option value="tornio">Tornio</option>\n<option value="turku" selected="selected">Turku</option>\n<option value="tuulos">Tuulos</option>\n<option value="tuusniemi">Tuusniemi</option>\n<option value="tuusula">Tuusula</option>\n<option value="tyrnava">Tyrn\xe4v\xe4</option>\n<option value="toysa">T\xf6ys\xe4</option>\n<option value="ullava">Ullava</option>\n<option value="ulvila">Ulvila</option>\n<option value="urjala">Urjala</option>\n<option value="utajarvi">Utaj\xe4rvi</option>\n<option value="utsjoki">Utsjoki</option>\n<option value="uurainen">Uurainen</option>\n<option value="uusikaarlepyy">Uusikaarlepyy</option>\n<option value="uusikaupunki">Uusikaupunki</option>\n<option value="vaala">Vaala</option>\n<option value="vaasa">Vaasa</option>\n<option value="vahto">Vahto</option>\n<option value="valkeakoski">Valkeakoski</option>\n<option value="valkeala">Valkeala</option>\n<option value="valtimo">Valtimo</option>\n<option value="vammala">Vammala</option>\n<option value="vampula">Vampula</option>\n<option value="vantaa">Vantaa</option>\n<option value="varkaus">Varkaus</option>\n<option value="varpaisjarvi">Varpaisj\xe4rvi</option>\n<option value="vehmaa">Vehmaa</option>\n<option value="velkua">Velkua</option>\n<option value="vesanto">Vesanto</option>\n<option value="vesilahti">Vesilahti</option>\n<option value="veteli">Veteli</option>\n<option value="vierema">Vierem\xe4</option>\n<option value="vihanti">Vihanti</option>\n<option value="vihti">Vihti</option>\n<option value="viitasaari">Viitasaari</option>\n<option value="vilppula">Vilppula</option>\n<option value="vimpeli">Vimpeli</option>\n<option value="virolahti">Virolahti</option>\n<option value="virrat">Virrat</option>\n<option value="vardo">V\xe5rd\xf6</option>\n<option value="vahakyro">V\xe4h\xe4kyr\xf6</option>\n<option value="vastanfjard">V\xe4stanfj\xe4rd</option>\n<option value="voyri-maksamaa">V\xf6yri-Maksamaa</option>\n<option value="yliharma">Ylih\xe4rm\xe4</option>\n<option value="yli-ii">Yli-Ii</option>\n<option value="ylikiiminki">Ylikiiminki</option>\n<option value="ylistaro">Ylistaro</option>\n<option value="ylitornio">Ylitornio</option>\n<option value="ylivieska">Ylivieska</option>\n<option value="ylamaa">Yl\xe4maa</option>\n<option value="ylane">Yl\xe4ne</option>\n<option value="ylojarvi">Yl\xf6j\xe4rvi</option>\n<option value="ypaja">Yp\xe4j\xe4</option>\n<option value="aetsa">\xc4ets\xe4</option>\n<option value="ahtari">\xc4ht\xe4ri</option>\n<option value="aanekoski">\xc4\xe4nekoski</option>\n</select>'

# FISocialSecurityNumber
##############################################################

>>> from django.contrib.localflavor.fi.forms import FISocialSecurityNumber
>>> f = FISocialSecurityNumber()
>>> f.clean('010101-0101')
u'010101-0101'
>>> f.clean('010101+0101')
u'010101+0101'
>>> f.clean('010101A0101')
u'010101A0101'
>>> f.clean('101010-0102')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Finnish social security number.']
>>> f.clean('10a010-0101')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Finnish social security number.']
>>> f.clean('101010-0\xe401')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Finnish social security number.']
>>> f.clean('101010b0101')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Finnish social security number.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f = FISocialSecurityNumber(required=False)
>>> f.clean('010101-0101')
u'010101-0101'
>>> f.clean(None)
u''
>>> f.clean('')
u''

#################################
# Tests of underlying functions #
#################################

# smart_unicode tests
>>> from django.newforms.util import smart_unicode
>>> class Test:
...     def __str__(self):
...        return 'ŠĐĆŽćžšđ'
>>> class TestU:
...     def __str__(self):
...        return 'Foo'
...     def __unicode__(self):
...        return u'\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111'
>>> smart_unicode(Test())
u'\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111'
>>> smart_unicode(TestU())
u'\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111'
>>> smart_unicode(1)
u'1'
>>> smart_unicode('foo')
u'foo'
"""

if __name__ == "__main__":
    import doctest
    doctest.testmod()
