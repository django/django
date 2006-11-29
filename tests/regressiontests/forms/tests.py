# -*- coding: utf-8 -*-
r"""
>>> from django.newforms import *
>>> import datetime
>>> import re

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
>>> w.render('is_cool', False)
u'<input type="checkbox" name="is_cool" />'
>>> w.render('is_cool', True)
u'<input checked="checked" type="checkbox" name="is_cool" />'
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

# CheckboxSelectMultiple Widget ###############################################

>>> w = CheckboxSelectMultiple()
>>> print w.render('beatles', ['J'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label><input checked="checked" type="checkbox" name="beatlesJ" /> John</label></li>
<li><label><input type="checkbox" name="beatlesP" /> Paul</label></li>
<li><label><input type="checkbox" name="beatlesG" /> George</label></li>
<li><label><input type="checkbox" name="beatlesR" /> Ringo</label></li>
</ul>
>>> print w.render('beatles', ['J', 'P'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label><input checked="checked" type="checkbox" name="beatlesJ" /> John</label></li>
<li><label><input checked="checked" type="checkbox" name="beatlesP" /> Paul</label></li>
<li><label><input type="checkbox" name="beatlesG" /> George</label></li>
<li><label><input type="checkbox" name="beatlesR" /> Ringo</label></li>
</ul>
>>> print w.render('beatles', ['J', 'P', 'R'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label><input checked="checked" type="checkbox" name="beatlesJ" /> John</label></li>
<li><label><input checked="checked" type="checkbox" name="beatlesP" /> Paul</label></li>
<li><label><input type="checkbox" name="beatlesG" /> George</label></li>
<li><label><input checked="checked" type="checkbox" name="beatlesR" /> Ringo</label></li>
</ul>

If the value is None, none of the options are selected:
>>> print w.render('beatles', None, choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label><input type="checkbox" name="beatlesJ" /> John</label></li>
<li><label><input type="checkbox" name="beatlesP" /> Paul</label></li>
<li><label><input type="checkbox" name="beatlesG" /> George</label></li>
<li><label><input type="checkbox" name="beatlesR" /> Ringo</label></li>
</ul>

If the value corresponds to a label (but not to an option value), none of the options are selected:
>>> print w.render('beatles', ['John'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label><input type="checkbox" name="beatlesJ" /> John</label></li>
<li><label><input type="checkbox" name="beatlesP" /> Paul</label></li>
<li><label><input type="checkbox" name="beatlesG" /> George</label></li>
<li><label><input type="checkbox" name="beatlesR" /> Ringo</label></li>
</ul>

If multiple values are given, but some of them are not valid, the valid ones are selected:
>>> print w.render('beatles', ['J', 'G', 'foo'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
<ul>
<li><label><input checked="checked" type="checkbox" name="beatlesJ" /> John</label></li>
<li><label><input type="checkbox" name="beatlesP" /> Paul</label></li>
<li><label><input checked="checked" type="checkbox" name="beatlesG" /> George</label></li>
<li><label><input type="checkbox" name="beatlesR" /> Ringo</label></li>
</ul>

The value is compared to its str():
>>> print w.render('nums', [2], choices=[('1', '1'), ('2', '2'), ('3', '3')])
<ul>
<li><label><input type="checkbox" name="nums1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums2" /> 2</label></li>
<li><label><input type="checkbox" name="nums3" /> 3</label></li>
</ul>
>>> print w.render('nums', ['2'], choices=[(1, 1), (2, 2), (3, 3)])
<ul>
<li><label><input type="checkbox" name="nums1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums2" /> 2</label></li>
<li><label><input type="checkbox" name="nums3" /> 3</label></li>
</ul>
>>> print w.render('nums', [2], choices=[(1, 1), (2, 2), (3, 3)])
<ul>
<li><label><input type="checkbox" name="nums1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums2" /> 2</label></li>
<li><label><input type="checkbox" name="nums3" /> 3</label></li>
</ul>

The 'choices' argument can be any iterable:
>>> def get_choices():
...     for i in range(5):
...         yield (i, i)
>>> print w.render('nums', [2], choices=get_choices())
<ul>
<li><label><input type="checkbox" name="nums0" /> 0</label></li>
<li><label><input type="checkbox" name="nums1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums2" /> 2</label></li>
<li><label><input type="checkbox" name="nums3" /> 3</label></li>
<li><label><input type="checkbox" name="nums4" /> 4</label></li>
</ul>

You can also pass 'choices' to the constructor:
>>> w = CheckboxSelectMultiple(choices=[(1, 1), (2, 2), (3, 3)])
>>> print w.render('nums', [2])
<ul>
<li><label><input type="checkbox" name="nums1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums2" /> 2</label></li>
<li><label><input type="checkbox" name="nums3" /> 3</label></li>
</ul>

If 'choices' is passed to both the constructor and render(), then they'll both be in the output:
>>> print w.render('nums', [2], choices=[(4, 4), (5, 5)])
<ul>
<li><label><input type="checkbox" name="nums1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums2" /> 2</label></li>
<li><label><input type="checkbox" name="nums3" /> 3</label></li>
<li><label><input type="checkbox" name="nums4" /> 4</label></li>
<li><label><input type="checkbox" name="nums5" /> 5</label></li>
</ul>

>>> w.render('nums', ['ŠĐĆŽćžšđ'], choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')])
u'<ul>\n<li><label><input type="checkbox" name="nums1" /> 1</label></li>\n<li><label><input type="checkbox" name="nums2" /> 2</label></li>\n<li><label><input type="checkbox" name="nums3" /> 3</label></li>\n<li><label><input checked="checked" type="checkbox" name="nums\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" /> \u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111</label></li>\n<li><label><input type="checkbox" name="nums\u0107\u017e\u0161\u0111" /> abc\u0107\u017e\u0161\u0111</label></li>\n</ul>'

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
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 10 characters.']
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
u''
>>> f.clean(None)
u''
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
>>> f = RegexField('^\d\d\d\d$', 'Enter a four-digit number.')
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
ValidationError: [u'Select a valid choice. 3 is not one of the available choices.']

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
ValidationError: [u'Select a valid choice. 3 is not one of the available choices.']

>>> f = ChoiceField(choices=[('J', 'John'), ('P', 'Paul')])
>>> f.clean('J')
u'J'
>>> f.clean('John')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. John is not one of the available choices.']

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

# Form ########################################################################

>>> class Person(Form):
...     first_name = CharField()
...     last_name = CharField()
...     birthday = DateField()

Pass a dictionary to a Form's __init__().
>>> p = Person({'first_name': u'John', 'last_name': u'Lennon', 'birthday': u'1940-10-9'})
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
<input type="text" name="first_name" value="John" />
>>> print p['last_name']
<input type="text" name="last_name" value="Lennon" />
>>> print p['birthday']
<input type="text" name="birthday" value="1940-10-9" />
>>> for boundfield in p:
...     print boundfield
<input type="text" name="first_name" value="John" />
<input type="text" name="last_name" value="Lennon" />
<input type="text" name="birthday" value="1940-10-9" />
>>> for boundfield in p:
...     print boundfield.verbose_name, boundfield.data
First name John
Last name Lennon
Birthday 1940-10-9
>>> print p
<tr><td>First name:</td><td><input type="text" name="first_name" value="John" /></td></tr>
<tr><td>Last name:</td><td><input type="text" name="last_name" value="Lennon" /></td></tr>
<tr><td>Birthday:</td><td><input type="text" name="birthday" value="1940-10-9" /></td></tr>

Empty dictionaries are valid, too.
>>> p = Person({})
>>> p.errors
{'first_name': [u'This field is required.'], 'last_name': [u'This field is required.'], 'birthday': [u'This field is required.']}
>>> p.is_valid()
False
>>> print p
<tr><td colspan="2"><ul class="errorlist"><li>This field is required.</li></ul></td></tr>
<tr><td>First name:</td><td><input type="text" name="first_name" /></td></tr>
<tr><td colspan="2"><ul class="errorlist"><li>This field is required.</li></ul></td></tr>
<tr><td>Last name:</td><td><input type="text" name="last_name" /></td></tr>
<tr><td colspan="2"><ul class="errorlist"><li>This field is required.</li></ul></td></tr>
<tr><td>Birthday:</td><td><input type="text" name="birthday" /></td></tr>
>>> print p.as_table()
<tr><td colspan="2"><ul class="errorlist"><li>This field is required.</li></ul></td></tr>
<tr><td>First name:</td><td><input type="text" name="first_name" /></td></tr>
<tr><td colspan="2"><ul class="errorlist"><li>This field is required.</li></ul></td></tr>
<tr><td>Last name:</td><td><input type="text" name="last_name" /></td></tr>
<tr><td colspan="2"><ul class="errorlist"><li>This field is required.</li></ul></td></tr>
<tr><td>Birthday:</td><td><input type="text" name="birthday" /></td></tr>
>>> print p.as_ul()
<li><ul class="errorlist"><li>This field is required.</li></ul>First name: <input type="text" name="first_name" /></li>
<li><ul class="errorlist"><li>This field is required.</li></ul>Last name: <input type="text" name="last_name" /></li>
<li><ul class="errorlist"><li>This field is required.</li></ul>Birthday: <input type="text" name="birthday" /></li>

If you don't pass any values to the Form's __init__(), or if you pass None,
the Form won't do any validation. Form.errors will be an empty dictionary *but*
Form.is_valid() will return False.
>>> p = Person()
>>> p.errors
{}
>>> p.is_valid()
False
>>> print p
<tr><td>First name:</td><td><input type="text" name="first_name" /></td></tr>
<tr><td>Last name:</td><td><input type="text" name="last_name" /></td></tr>
<tr><td>Birthday:</td><td><input type="text" name="birthday" /></td></tr>
>>> print p.as_table()
<tr><td>First name:</td><td><input type="text" name="first_name" /></td></tr>
<tr><td>Last name:</td><td><input type="text" name="last_name" /></td></tr>
<tr><td>Birthday:</td><td><input type="text" name="birthday" /></td></tr>
>>> print p.as_ul()
<li>First name: <input type="text" name="first_name" /></li>
<li>Last name: <input type="text" name="last_name" /></li>
<li>Birthday: <input type="text" name="birthday" /></li>

Unicode values are handled properly.
>>> p = Person({'first_name': u'John', 'last_name': u'\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111', 'birthday': '1940-10-9'})
>>> p.as_table()
u'<tr><td>First name:</td><td><input type="text" name="first_name" value="John" /></td></tr>\n<tr><td>Last name:</td><td><input type="text" name="last_name" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" /></td></tr>\n<tr><td>Birthday:</td><td><input type="text" name="birthday" value="1940-10-9" /></td></tr>'
>>> p.as_ul()
u'<li>First name: <input type="text" name="first_name" value="John" /></li>\n<li>Last name: <input type="text" name="last_name" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" /></li>\n<li>Birthday: <input type="text" name="birthday" value="1940-10-9" /></li>'

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
>>> repr(p.clean_data)
'None'
>>> p['first_name'].errors
[u'This field is required.']
>>> p['first_name'].errors.as_ul()
u'<ul class="errorlist"><li>This field is required.</li></ul>'
>>> p['first_name'].errors.as_text()
u'* This field is required.'

>>> p = Person()
>>> print p['first_name']
<input type="text" name="first_name" />
>>> print p['last_name']
<input type="text" name="last_name" />
>>> print p['birthday']
<input type="text" name="birthday" />

"auto_id" tells the Form to add an "id" attribute to each form element.
If it's a string that contains '%s', Django will use that as a format string
into which the field's name will be inserted. It will also put a <label> around
the human-readable labels for a field.
>>> p = Person(auto_id='id_%s')
>>> print p.as_ul()
<li><label for="id_first_name">First name:</label> <input type="text" name="first_name" id="id_first_name" /></li>
<li><label for="id_last_name">Last name:</label> <input type="text" name="last_name" id="id_last_name" /></li>
<li><label for="id_birthday">Birthday:</label> <input type="text" name="birthday" id="id_birthday" /></li>
>>> print p.as_table()
<tr><td><label for="id_first_name">First name:</label></td><td><input type="text" name="first_name" id="id_first_name" /></td></tr>
<tr><td><label for="id_last_name">Last name:</label></td><td><input type="text" name="last_name" id="id_last_name" /></td></tr>
<tr><td><label for="id_birthday">Birthday:</label></td><td><input type="text" name="birthday" id="id_birthday" /></td></tr>

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
>>> f = SignupForm()
>>> print f['email']
<input type="text" name="email" />
>>> print f['get_spam']
<input type="checkbox" name="get_spam" />

>>> f = SignupForm({'email': 'test@example.com', 'get_spam': True})
>>> print f['email']
<input type="text" name="email" value="test@example.com" />
>>> print f['get_spam']
<input checked="checked" type="checkbox" name="get_spam" />

Any Field can have a Widget class passed to its constructor:
>>> class ContactForm(Form):
...     subject = CharField()
...     message = CharField(widget=Textarea)
>>> f = ContactForm()
>>> print f['subject']
<input type="text" name="subject" />
>>> print f['message']
<textarea name="message"></textarea>

as_textarea() and as_text() are shortcuts for changing the output widget type:
>>> f['subject'].as_textarea()
u'<textarea name="subject"></textarea>'
>>> f['message'].as_text()
u'<input type="text" name="message" />'

The 'widget' parameter to a Field can also be an instance:
>>> class ContactForm(Form):
...     subject = CharField()
...     message = CharField(widget=Textarea(attrs={'rows': 80, 'cols': 20}))
>>> f = ContactForm()
>>> print f['message']
<textarea rows="80" cols="20" name="message"></textarea>

Instance-level attrs are *not* carried over to as_textarea() and as_text():
>>> f['message'].as_text()
u'<input type="text" name="message" />'
>>> f = ContactForm({'subject': 'Hello', 'message': 'I love you.'})
>>> f['subject'].as_textarea()
u'<textarea name="subject">Hello</textarea>'
>>> f['message'].as_text()
u'<input type="text" name="message" value="I love you." />'

For a form with a <select>, use ChoiceField:
>>> class FrameworkForm(Form):
...     name = CharField()
...     language = ChoiceField(choices=[('P', 'Python'), ('J', 'Java')])
>>> f = FrameworkForm()
>>> print f['language']
<select name="language">
<option value="P">Python</option>
<option value="J">Java</option>
</select>
>>> f = FrameworkForm({'name': 'Django', 'language': 'P'})
>>> print f['language']
<select name="language">
<option value="P" selected="selected">Python</option>
<option value="J">Java</option>
</select>

Add widget=RadioSelect to use that widget with a ChoiceField.
>>> class FrameworkForm(Form):
...     name = CharField()
...     language = ChoiceField(choices=[('P', 'Python'), ('J', 'Java')], widget=RadioSelect)
>>> f = FrameworkForm()
>>> print f['language']
<ul>
<li><label><input type="radio" name="language" value="P" /> Python</label></li>
<li><label><input type="radio" name="language" value="J" /> Java</label></li>
</ul>
>>> print f
<tr><td>Name:</td><td><input type="text" name="name" /></td></tr>
<tr><td>Language:</td><td><ul>
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
<tr><td><label for="id_name">Name:</label></td><td><input type="text" name="name" id="id_name" /></td></tr>
<tr><td><label for="id_language_0">Language:</label></td><td><ul>
<li><label><input type="radio" id="id_language_0" value="P" name="language" /> Python</label></li>
<li><label><input type="radio" id="id_language_1" value="J" name="language" /> Java</label></li>
</ul></td></tr>
>>> print f.as_ul()
<li><label for="id_name">Name:</label> <input type="text" name="name" id="id_name" /></li>
<li><label for="id_language_0">Language:</label> <ul>
<li><label><input type="radio" id="id_language_0" value="P" name="language" /> Python</label></li>
<li><label><input type="radio" id="id_language_1" value="J" name="language" /> Java</label></li>
</ul></li>

MultipleChoiceField is a special case, as its data is required to be a list:
>>> class SongForm(Form):
...     name = CharField()
...     composers = MultipleChoiceField()
>>> f = SongForm()
>>> print f['composers']
<select multiple="multiple" name="composers">
</select>
>>> class SongForm(Form):
...     name = CharField()
...     composers = MultipleChoiceField(choices=[('J', 'John Lennon'), ('P', 'Paul McCartney')])
>>> f = SongForm()
>>> print f['composers']
<select multiple="multiple" name="composers">
<option value="J">John Lennon</option>
<option value="P">Paul McCartney</option>
</select>
>>> f = SongForm({'name': 'Yesterday', 'composers': ['P']})
>>> print f['name']
<input type="text" name="name" value="Yesterday" />
>>> print f['composers']
<select multiple="multiple" name="composers">
<option value="J">John Lennon</option>
<option value="P" selected="selected">Paul McCartney</option>
</select>

MultipleChoiceField can also be used with the CheckboxSelectMultiple widget.
>>> class SongForm(Form):
...     name = CharField()
...     composers = MultipleChoiceField(choices=[('J', 'John Lennon'), ('P', 'Paul McCartney')], widget=CheckboxSelectMultiple)
>>> f = SongForm()
>>> print f['composers']
<ul>
<li><label><input type="checkbox" name="composersJ" /> John Lennon</label></li>
<li><label><input type="checkbox" name="composersP" /> Paul McCartney</label></li>
</ul>
>>> f = SongForm({'composers': ['J']})
>>> print f['composers']
<ul>
<li><label><input checked="checked" type="checkbox" name="composersJ" /> John Lennon</label></li>
<li><label><input type="checkbox" name="composersP" /> Paul McCartney</label></li>
</ul>
>>> f = SongForm({'composers': ['J', 'P']})
>>> print f['composers']
<ul>
<li><label><input checked="checked" type="checkbox" name="composersJ" /> John Lennon</label></li>
<li><label><input checked="checked" type="checkbox" name="composersP" /> Paul McCartney</label></li>
</ul>

When using CheckboxSelectMultiple, the framework automatically converts the
data in clean_data to a list of values, rather than the underlying HTML form
field name.
>>> f = SongForm({'name': 'Yesterday'})
>>> f.errors
{'composers': [u'This field is required.']}
>>> f = SongForm({'name': 'Yesterday', 'composersJ': 'on'})
>>> f.errors
{}
>>> f.clean_data
{'composers': [u'J'], 'name': u'Yesterday'}
>>> f = SongForm({'name': 'Yesterday', 'composersJ': 'on', 'composersP': 'on'})
>>> f.errors
{}
>>> f.clean_data
{'composers': [u'J', u'P'], 'name': u'Yesterday'}

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
>>> f = UserRegistration()
>>> f.errors
{}
>>> f = UserRegistration({})
>>> f.errors
{'username': [u'This field is required.'], 'password1': [u'This field is required.'], 'password2': [u'This field is required.']}
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'bar'})
>>> f.errors
{'password2': [u'Please make sure your passwords match.']}
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'foo'})
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
>>> f = UserRegistration()
>>> f.errors
{}
>>> f = UserRegistration({})
>>> print f.as_table()
<tr><td colspan="2"><ul class="errorlist"><li>This field is required.</li></ul></td></tr>
<tr><td>Username:</td><td><input type="text" name="username" /></td></tr>
<tr><td colspan="2"><ul class="errorlist"><li>This field is required.</li></ul></td></tr>
<tr><td>Password1:</td><td><input type="password" name="password1" /></td></tr>
<tr><td colspan="2"><ul class="errorlist"><li>This field is required.</li></ul></td></tr>
<tr><td>Password2:</td><td><input type="password" name="password2" /></td></tr>
>>> f.errors
{'username': [u'This field is required.'], 'password1': [u'This field is required.'], 'password2': [u'This field is required.']}
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'bar'})
>>> f.errors
{'__all__': [u'Please make sure your passwords match.']}
>>> print f.as_table()
<tr><td colspan="2"><ul class="errorlist"><li>Please make sure your passwords match.</li></ul></td></tr>
<tr><td>Username:</td><td><input type="text" name="username" value="adrian" /></td></tr>
<tr><td>Password1:</td><td><input type="password" name="password1" value="foo" /></td></tr>
<tr><td>Password2:</td><td><input type="password" name="password2" value="bar" /></td></tr>
>>> print f.as_ul()
<li><ul class="errorlist"><li>Please make sure your passwords match.</li></ul></li>
<li>Username: <input type="text" name="username" value="adrian" /></li>
<li>Password1: <input type="password" name="password1" value="foo" /></li>
<li>Password2: <input type="password" name="password2" value="bar" /></li>
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'foo'})
>>> f.errors
{}
>>> f.clean_data
{'username': u'adrian', 'password1': u'foo', 'password2': u'foo'}

It's possible to construct a Form dynamically by adding to the self.fields
dictionary in __init__(). Don't forget to call Form.__init__() within the
subclass' __init__().
>>> class Person(Form):
...     first_name = CharField()
...     last_name = CharField()
...     def __init__(self):
...         super(Person, self).__init__()
...         self.fields['birthday'] = DateField()
>>> p = Person()
>>> print p
<tr><td>First name:</td><td><input type="text" name="first_name" /></td></tr>
<tr><td>Last name:</td><td><input type="text" name="last_name" /></td></tr>
<tr><td>Birthday:</td><td><input type="text" name="birthday" /></td></tr>

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
>>> p = TestForm()
>>> print p
<tr><td>Field1:</td><td><input type="text" name="field1" /></td></tr>
<tr><td>Field2:</td><td><input type="text" name="field2" /></td></tr>
<tr><td>Field3:</td><td><input type="text" name="field3" /></td></tr>
<tr><td>Field4:</td><td><input type="text" name="field4" /></td></tr>
<tr><td>Field5:</td><td><input type="text" name="field5" /></td></tr>
<tr><td>Field6:</td><td><input type="text" name="field6" /></td></tr>
<tr><td>Field7:</td><td><input type="text" name="field7" /></td></tr>
<tr><td>Field8:</td><td><input type="text" name="field8" /></td></tr>
<tr><td>Field9:</td><td><input type="text" name="field9" /></td></tr>
<tr><td>Field10:</td><td><input type="text" name="field10" /></td></tr>
<tr><td>Field11:</td><td><input type="text" name="field11" /></td></tr>
<tr><td>Field12:</td><td><input type="text" name="field12" /></td></tr>
<tr><td>Field13:</td><td><input type="text" name="field13" /></td></tr>
<tr><td>Field14:</td><td><input type="text" name="field14" /></td></tr>

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
...         form = UserRegistration(post_data)
...     else:
...         form = UserRegistration()
...     if form.is_valid():
...         return 'VALID: %r' % form.clean_data
...     t = Template('<form action="" method="post">\n<table>\n{{ form }}\n</table>\n<input type="submit" />\n</form>')
...     return t.render(Context({'form': form}))

Case 1: GET (an empty form, with no errors).
>>> print my_function('GET', {})
<form action="" method="post">
<table>
<tr><td>Username:</td><td><input type="text" name="username" /></td></tr>
<tr><td>Password1:</td><td><input type="password" name="password1" /></td></tr>
<tr><td>Password2:</td><td><input type="password" name="password2" /></td></tr>
</table>
<input type="submit" />
</form>

Case 2: POST with erroneous data (a redisplayed form, with errors).
>>> print my_function('POST', {'username': 'this-is-a-long-username', 'password1': 'foo', 'password2': 'bar'})
<form action="" method="post">
<table>
<tr><td colspan="2"><ul class="errorlist"><li>Please make sure your passwords match.</li></ul></td></tr>
<tr><td colspan="2"><ul class="errorlist"><li>Ensure this value has at most 10 characters.</li></ul></td></tr>
<tr><td>Username:</td><td><input type="text" name="username" value="this-is-a-long-username" /></td></tr>
<tr><td>Password1:</td><td><input type="password" name="password1" value="foo" /></td></tr>
<tr><td>Password2:</td><td><input type="password" name="password2" value="bar" /></td></tr>
</table>
<input type="submit" />
</form>

Case 3: POST with valid data (the success message).
>>> print my_function('POST', {'username': 'adrian', 'password1': 'secret', 'password2': 'secret'})
VALID: {'username': u'adrian', 'password1': u'secret', 'password2': u'secret'}

# Some ideas for using templates with forms ###################################

>>> class UserRegistration(Form):
...    username = CharField(max_length=10)
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
>>> print t.render(Context({'form': UserRegistration()}))
<form action="">
<p><label>Your username: <input type="text" name="username" /></label></p>
<p><label>Password: <input type="password" name="password1" /></label></p>
<p><label>Password (again): <input type="password" name="password2" /></label></p>
<input type="submit" />
</form>
>>> print t.render(Context({'form': UserRegistration({'username': 'django'})}))
<form action="">
<p><label>Your username: <input type="text" name="username" value="django" /></label></p>
<ul class="errorlist"><li>This field is required.</li></ul><p><label>Password: <input type="password" name="password1" /></label></p>
<ul class="errorlist"><li>This field is required.</li></ul><p><label>Password (again): <input type="password" name="password2" /></label></p>
<input type="submit" />
</form>

Use form.[field].verbose_name to output a field's "verbose name" -- its field
name with underscores converted to spaces, and the initial letter capitalized.
>>> t = Template('''<form action="">
... <p><label>{{ form.username.verbose_name }}: {{ form.username }}</label></p>
... <p><label>{{ form.password1.verbose_name }}: {{ form.password1 }}</label></p>
... <p><label>{{ form.password2.verbose_name }}: {{ form.password2 }}</label></p>
... <input type="submit" />
... </form>''')
>>> print t.render(Context({'form': UserRegistration()}))
<form action="">
<p><label>Username: <input type="text" name="username" /></label></p>
<p><label>Password1: <input type="password" name="password1" /></label></p>
<p><label>Password2: <input type="password" name="password2" /></label></p>
<input type="submit" />
</form>

User form.[field].label_tag to output a field's verbose_name with a <label>
tag wrapped around it, but *only* if the given field has an "id" attribute.
Recall from above that passing the "auto_id" argument to a Form gives each
field an "id" attribute.
>>> t = Template('''<form action="">
... <p>{{ form.username.label_tag }}: {{ form.username }}</p>
... <p>{{ form.password1.label_tag }}: {{ form.password1 }}</p>
... <p>{{ form.password2.label_tag }}: {{ form.password2 }}</p>
... <input type="submit" />
... </form>''')
>>> print t.render(Context({'form': UserRegistration()}))
<form action="">
<p>Username: <input type="text" name="username" /></p>
<p>Password1: <input type="password" name="password1" /></p>
<p>Password2: <input type="password" name="password2" /></p>
<input type="submit" />
</form>
>>> print t.render(Context({'form': UserRegistration(auto_id='id_%s')}))
<form action="">
<p><label for="id_username">Username</label>: <input type="text" name="username" id="id_username" /></p>
<p><label for="id_password1">Password1</label>: <input type="password" name="password1" id="id_password1" /></p>
<p><label for="id_password2">Password2</label>: <input type="password" name="password2" id="id_password2" /></p>
<input type="submit" />
</form>

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
>>> print t.render(Context({'form': UserRegistration({'username': 'django', 'password1': 'foo', 'password2': 'bar'})}))
<form action="">
<p><label>Your username: <input type="text" name="username" value="django" /></label></p>
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
>>> print t.render(Context({'form': UserRegistration({'username': 'django', 'password1': 'foo', 'password2': 'bar'})}))
<form action="">
<ul class="errorlist"><li>Please make sure your passwords match.</li></ul>
<p><label>Your username: <input type="text" name="username" value="django" /></label></p>
<p><label>Password: <input type="password" name="password1" value="foo" /></label></p>
<p><label>Password (again): <input type="password" name="password2" value="bar" /></label></p>
<input type="submit" />
</form>
"""

if __name__ == "__main__":
    import doctest
    doctest.testmod()
