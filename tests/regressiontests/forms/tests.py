"""
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

'attrs' passed to render() get precedence over those passed to the constructor:
>>> w = HiddenInput(attrs={'class': 'pretty'})
>>> w.render('email', '', attrs={'class': 'special'})
u'<input type="hidden" class="special" name="email" />'

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

# CharField ###################################################################

>>> f = CharField(required=False)
>>> f.clean(1)
u'1'
>>> f.clean('hello')
u'hello'
>>> f.clean(None)
u''
>>> f.clean([1, 2, 3])
u'[1, 2, 3]'

CharField accepts an optional max_length parameter:
>>> f = CharField(max_length=10, required=False)
>>> f.clean('')
u''
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
>>> f.clean(1)
u'1'
>>> f.clean('1')
u'1'
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
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

# ComboField ##################################################################

ComboField takes a list of fields that should be used to validate a value,
in that order:
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

# Form ########################################################################

>>> class Person(Form):
...     first_name = CharField()
...     last_name = CharField()
...     birthday = DateField()
>>> p = Person()
>>> print p
<table>
<tr><td>First name:</td><td><input type="text" name="first_name" /></td></tr>
<tr><td>Last name:</td><td><input type="text" name="last_name" /></td></tr>
<tr><td>Birthday:</td><td><input type="text" name="birthday" /></td></tr>
</table>
>>> print p.as_table()
<table>
<tr><td>First name:</td><td><input type="text" name="first_name" /></td></tr>
<tr><td>Last name:</td><td><input type="text" name="last_name" /></td></tr>
<tr><td>Birthday:</td><td><input type="text" name="birthday" /></td></tr>
</table>
>>> print p.as_ul()
<ul>
<li>First name: <input type="text" name="first_name" /></li>
<li>Last name: <input type="text" name="last_name" /></li>
<li>Birthday: <input type="text" name="birthday" /></li>
</ul>
>>> print p.as_table_with_errors()
<table>
<tr><td colspan="2"><ul><li>This field is required.</li></ul></td></tr>
<tr><td>First name:</td><td><input type="text" name="first_name" /></td></tr>
<tr><td colspan="2"><ul><li>This field is required.</li></ul></td></tr>
<tr><td>Last name:</td><td><input type="text" name="last_name" /></td></tr>
<tr><td colspan="2"><ul><li>This field is required.</li></ul></td></tr>
<tr><td>Birthday:</td><td><input type="text" name="birthday" /></td></tr>
</table>
>>> print p.as_ul_with_errors()
<ul>
<li><ul><li>This field is required.</li></ul>First name: <input type="text" name="first_name" /></li>
<li><ul><li>This field is required.</li></ul>Last name: <input type="text" name="last_name" /></li>
<li><ul><li>This field is required.</li></ul>Birthday: <input type="text" name="birthday" /></li>
</ul>

>>> p = Person({'first_name': u'John', 'last_name': u'Lennon', 'birthday': u'1940-10-9'})
>>> p.errors()
{}
>>> p.is_valid()
True
>>> p.errors().as_ul()
u''
>>> p.errors().as_text()
u''
>>> p.clean()
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
>>> print p
<table>
<tr><td>First name:</td><td><input type="text" name="first_name" value="John" /></td></tr>
<tr><td>Last name:</td><td><input type="text" name="last_name" value="Lennon" /></td></tr>
<tr><td>Birthday:</td><td><input type="text" name="birthday" value="1940-10-9" /></td></tr>
</table>

>>> p = Person({'last_name': u'Lennon'})
>>> p.errors()
{'first_name': [u'This field is required.'], 'birthday': [u'This field is required.']}
>>> p.is_valid()
False
>>> p.errors().as_ul()
u'<ul class="errorlist"><li>first_name<ul class="errorlist"><li>This field is required.</li></ul></li><li>birthday<ul class="errorlist"><li>This field is required.</li></ul></li></ul>'
>>> print p.errors().as_text()
* first_name
  * This field is required.
* birthday
  * This field is required.
>>> p.clean()
>>> repr(p.clean())
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
into which the field's name will be inserted.
>>> p = Person(auto_id='id_%s')
>>> print p.as_ul()
<ul>
<li>First name: <input type="text" name="first_name" id="id_first_name" /></li>
<li>Last name: <input type="text" name="last_name" id="id_last_name" /></li>
<li>Birthday: <input type="text" name="birthday" id="id_birthday" /></li>
</ul>

If auto_id is any True value whose str() does not contain '%s', the "id"
attribute will be the name of the field.
>>> p = Person(auto_id=True)
>>> print p.as_ul()
<ul>
<li>First name: <input type="text" name="first_name" id="first_name" /></li>
<li>Last name: <input type="text" name="last_name" id="last_name" /></li>
<li>Birthday: <input type="text" name="birthday" id="birthday" /></li>
</ul>

If auto_id is any False value, an "id" attribute won't be output unless it
was manually entered.
>>> p = Person(auto_id=False)
>>> print p.as_ul()
<ul>
<li>First name: <input type="text" name="first_name" /></li>
<li>Last name: <input type="text" name="last_name" /></li>
<li>Birthday: <input type="text" name="birthday" /></li>
</ul>

In this example, auto_id is False, but the "id" attribute for the "first_name"
field is given.
>>> class PersonNew(Form):
...     first_name = CharField(widget=TextInput(attrs={'id': 'first_name_id'}))
...     last_name = CharField()
...     birthday = DateField()
>>> p = PersonNew(auto_id=False)
>>> print p.as_ul()
<ul>
<li>First name: <input type="text" id="first_name_id" name="first_name" /></li>
<li>Last name: <input type="text" name="last_name" /></li>
<li>Birthday: <input type="text" name="birthday" /></li>
</ul>

If the "id" attribute is specified in the Form and auto_id is True, the "id"
attribute in the Form gets precedence.
>>> p = PersonNew(auto_id=True)
>>> print p.as_ul()
<ul>
<li>First name: <input type="text" id="first_name_id" name="first_name" /></li>
<li>Last name: <input type="text" name="last_name" id="last_name" /></li>
<li>Birthday: <input type="text" name="birthday" id="birthday" /></li>
</ul>

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

There are a couple of ways to do multiple-field validation. If you want the
validation message to be associated with a particular field, implement the
clean_XXX() method on the Form, where XXX is the field name. As in
Field.clean(), the clean_XXX() method should return the cleaned value:
>>> class UserRegistration(Form):
...    username = CharField(max_length=10)
...    password1 = CharField(widget=PasswordInput)
...    password2 = CharField(widget=PasswordInput)
...    def clean_password2(self):
...        if self.clean_data.get('password1') and self.clean_data.get('password2') and self.clean_data['password1'] != self.clean_data['password2']:
...            raise ValidationError(u'Please make sure your passwords match.')
...        return self.clean_data['password2']
>>> f = UserRegistration()
>>> f.errors()
{'username': [u'This field is required.'], 'password1': [u'This field is required.'], 'password2': [u'This field is required.']}
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'bar'})
>>> f.errors()
{'password2': [u'Please make sure your passwords match.']}
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'foo'})
>>> f.errors()
{}
>>> f.clean()
{'username': u'adrian', 'password1': u'foo', 'password2': u'foo'}

Another way of doing multiple-field validation is by implementing the
Form's clean() method. If you do this, any ValidationError raised by that
method will not be associated with a particular field; it will have a
special-case association with the field named '__all__'. Note that
Form.clean() still needs to return a dictionary of all clean data:
>>> class UserRegistration(Form):
...    username = CharField(max_length=10)
...    password1 = CharField(widget=PasswordInput)
...    password2 = CharField(widget=PasswordInput)
...    def clean(self):
...        if self.clean_data.get('password1') and self.clean_data.get('password2') and self.clean_data['password1'] != self.clean_data['password2']:
...            raise ValidationError(u'Please make sure your passwords match.')
...        return self.clean_data
>>> f = UserRegistration()
>>> print f.as_table()
<table>
<tr><td>Username:</td><td><input type="text" name="username" /></td></tr>
<tr><td>Password1:</td><td><input type="password" name="password1" /></td></tr>
<tr><td>Password2:</td><td><input type="password" name="password2" /></td></tr>
</table>
>>> f.errors()
{'username': [u'This field is required.'], 'password1': [u'This field is required.'], 'password2': [u'This field is required.']}
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'bar'})
>>> f.errors()
{'__all__': [u'Please make sure your passwords match.']}
>>> print f.as_table()
<table>
<tr><td>Username:</td><td><input type="text" name="username" value="adrian" /></td></tr>
<tr><td>Password1:</td><td><input type="password" name="password1" value="foo" /></td></tr>
<tr><td>Password2:</td><td><input type="password" name="password2" value="bar" /></td></tr>
</table>
>>> print f.as_table_with_errors()
<table>
<tr><td colspan="2"><ul><li>Please make sure your passwords match.</li></ul></td></tr>
<tr><td>Username:</td><td><input type="text" name="username" value="adrian" /></td></tr>
<tr><td>Password1:</td><td><input type="password" name="password1" value="foo" /></td></tr>
<tr><td>Password2:</td><td><input type="password" name="password2" value="bar" /></td></tr>
</table>
>>> print f.as_ul_with_errors()
<ul>
<li><ul><li>Please make sure your passwords match.</li></ul></li>
<li>Username: <input type="text" name="username" value="adrian" /></li>
<li>Password1: <input type="password" name="password1" value="foo" /></li>
<li>Password2: <input type="password" name="password2" value="bar" /></li>
</ul>
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'foo'})
>>> f.errors()
{}
>>> f.clean()
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
<table>
<tr><td>First name:</td><td><input type="text" name="first_name" /></td></tr>
<tr><td>Last name:</td><td><input type="text" name="last_name" /></td></tr>
<tr><td>Birthday:</td><td><input type="text" name="birthday" /></td></tr>
</table>
"""

if __name__ == "__main__":
    import doctest
    doctest.testmod()
