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

# CharField ###################################################################

>>> f = CharField(required=False)
>>> f.to_python(1)
u'1'
>>> f.to_python('hello')
u'hello'
>>> f.to_python(None)
u''
>>> f.to_python([1, 2, 3])
u'[1, 2, 3]'

CharField accepts an optional max_length parameter:
>>> f = CharField(max_length=10, required=False)
>>> f.to_python('')
u''
>>> f.to_python('12345')
u'12345'
>>> f.to_python('1234567890')
u'1234567890'
>>> f.to_python('1234567890a')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 10 characters.']

CharField accepts an optional min_length parameter:
>>> f = CharField(min_length=10, required=False)
>>> f.to_python('')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 10 characters.']
>>> f.to_python('12345')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 10 characters.']
>>> f.to_python('1234567890')
u'1234567890'
>>> f.to_python('1234567890a')
u'1234567890a'

# IntegerField ################################################################

>>> f = IntegerField()
>>> f.to_python('1')
1
>>> isinstance(f.to_python('1'), int)
True
>>> f.to_python('23')
23
>>> f.to_python('a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a whole number.']
>>> f.to_python('1 ')
1
>>> f.to_python(' 1')
1
>>> f.to_python(' 1 ')
1
>>> f.to_python('1a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a whole number.']

# DateField ###################################################################

>>> import datetime
>>> f = DateField()
>>> f.to_python(datetime.date(2006, 10, 25))
datetime.date(2006, 10, 25)
>>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30))
datetime.date(2006, 10, 25)
>>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30, 59))
datetime.date(2006, 10, 25)
>>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30, 59, 200))
datetime.date(2006, 10, 25)
>>> f.to_python('2006-10-25')
datetime.date(2006, 10, 25)
>>> f.to_python('10/25/2006')
datetime.date(2006, 10, 25)
>>> f.to_python('10/25/06')
datetime.date(2006, 10, 25)
>>> f.to_python('Oct 25 2006')
datetime.date(2006, 10, 25)
>>> f.to_python('October 25 2006')
datetime.date(2006, 10, 25)
>>> f.to_python('October 25, 2006')
datetime.date(2006, 10, 25)
>>> f.to_python('25 October 2006')
datetime.date(2006, 10, 25)
>>> f.to_python('25 October, 2006')
datetime.date(2006, 10, 25)
>>> f.to_python('2006-4-31')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.to_python('200a-10-25')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.to_python('25/10/06')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.to_python(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = DateField(required=False)
>>> f.to_python(None)
>>> repr(f.to_python(None))
'None'
>>> f.to_python('')
>>> repr(f.to_python(''))
'None'

DateField accepts an optional input_formats parameter:
>>> f = DateField(input_formats=['%Y %m %d'])
>>> f.to_python(datetime.date(2006, 10, 25))
datetime.date(2006, 10, 25)
>>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30))
datetime.date(2006, 10, 25)
>>> f.to_python('2006 10 25')
datetime.date(2006, 10, 25)

The input_formats parameter overrides all default input formats,
so the default formats won't work unless you specify them:
>>> f.to_python('2006-10-25')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.to_python('10/25/2006')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.to_python('10/25/06')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']

# DateTimeField ###############################################################

>>> import datetime
>>> f = DateTimeField()
>>> f.to_python(datetime.date(2006, 10, 25))
datetime.datetime(2006, 10, 25, 0, 0)
>>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30))
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30, 59))
datetime.datetime(2006, 10, 25, 14, 30, 59)
>>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30, 59, 200))
datetime.datetime(2006, 10, 25, 14, 30, 59, 200)
>>> f.to_python('2006-10-25 14:30:45')
datetime.datetime(2006, 10, 25, 14, 30, 45)
>>> f.to_python('2006-10-25 14:30:00')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.to_python('2006-10-25 14:30')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.to_python('2006-10-25')
datetime.datetime(2006, 10, 25, 0, 0)
>>> f.to_python('10/25/2006 14:30:45')
datetime.datetime(2006, 10, 25, 14, 30, 45)
>>> f.to_python('10/25/2006 14:30:00')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.to_python('10/25/2006 14:30')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.to_python('10/25/2006')
datetime.datetime(2006, 10, 25, 0, 0)
>>> f.to_python('10/25/06 14:30:45')
datetime.datetime(2006, 10, 25, 14, 30, 45)
>>> f.to_python('10/25/06 14:30:00')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.to_python('10/25/06 14:30')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.to_python('10/25/06')
datetime.datetime(2006, 10, 25, 0, 0)
>>> f.to_python('hello')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date/time.']
>>> f.to_python('2006-10-25 4:30 p.m.')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date/time.']

DateField accepts an optional input_formats parameter:
>>> f = DateTimeField(input_formats=['%Y %m %d %I:%M %p'])
>>> f.to_python(datetime.date(2006, 10, 25))
datetime.datetime(2006, 10, 25, 0, 0)
>>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30))
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30, 59))
datetime.datetime(2006, 10, 25, 14, 30, 59)
>>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30, 59, 200))
datetime.datetime(2006, 10, 25, 14, 30, 59, 200)
>>> f.to_python('2006 10 25 2:30 PM')
datetime.datetime(2006, 10, 25, 14, 30)

The input_formats parameter overrides all default input formats,
so the default formats won't work unless you specify them:
>>> f.to_python('2006-10-25 14:30:45')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date/time.']

# RegexField ##################################################################

>>> f = RegexField('^\d[A-F]\d$')
>>> f.to_python('2A2')
u'2A2'
>>> f.to_python('3F3')
u'3F3'
>>> f.to_python('3G3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.to_python(' 2A2')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.to_python('2A2 ')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']

Alternatively, RegexField can take a compiled regular expression:
>>> f = RegexField(re.compile('^\d[A-F]\d$'))
>>> f.to_python('2A2')
u'2A2'
>>> f.to_python('3F3')
u'3F3'
>>> f.to_python('3G3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.to_python(' 2A2')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.to_python('2A2 ')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']

RegexField takes an optional error_message argument:
>>> f = RegexField('^\d\d\d\d$', 'Enter a four-digit number.')
>>> f.to_python('1234')
u'1234'
>>> f.to_python('123')
Traceback (most recent call last):
...
ValidationError: [u'Enter a four-digit number.']
>>> f.to_python('abcd')
Traceback (most recent call last):
...
ValidationError: [u'Enter a four-digit number.']

# EmailField ##################################################################

>>> f = EmailField()
>>> f.to_python('person@example.com')
u'person@example.com'
>>> f.to_python('foo')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']
>>> f.to_python('foo@')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']
>>> f.to_python('foo@bar')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']

# URLField ##################################################################

>>> f = URLField()
>>> f.to_python('http://example.com')
u'http://example.com'
>>> f.to_python('http://www.example.com')
u'http://www.example.com'
>>> f.to_python('foo')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.to_python('example.com')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.to_python('http://')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.to_python('http://example')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.to_python('http://example.')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.to_python('http://.com')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']

URLField takes an optional verify_exists parameter, which is False by default.
This verifies that the URL is live on the Internet and doesn't return a 404 or 500:
>>> f = URLField(verify_exists=True)
>>> f.to_python('http://www.google.com')
u'http://www.google.com'
>>> f.to_python('http://example')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.to_python('http://www.jfoiwjfoi23jfoijoaijfoiwjofiwjefewl.com') # bad domain
Traceback (most recent call last):
...
ValidationError: [u'This URL appears to be a broken link.']
>>> f.to_python('http://google.com/we-love-microsoft.html') # good domain, bad page
Traceback (most recent call last):
...
ValidationError: [u'This URL appears to be a broken link.']

# BooleanField ################################################################

>>> f = BooleanField()
>>> f.to_python(True)
True
>>> f.to_python(False)
False
>>> f.to_python(1)
True
>>> f.to_python(0)
False
>>> f.to_python('Django rocks')
True

# Form ########################################################################

>>> class Person(Form):
...     first_name = CharField()
...     last_name = CharField()
...     birthday = DateField()
>>> p = Person({'first_name': u'John', 'last_name': u'Lennon', 'birthday': u'1940-10-9'})
>>> p.errors()
{}
>>> p.is_valid()
True
>>> p.errors().as_ul()
u''
>>> p.errors().as_text()
u''
>>> p.to_python()
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
>>> p.to_python()
>>> repr(p.to_python())
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

"""

if __name__ == "__main__":
    import doctest
    doctest.testmod()
