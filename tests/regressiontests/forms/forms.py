# -*- coding: utf-8 -*-
tests = r"""
>>> from django.forms import *
>>> from django.core.files.uploadedfile import SimpleUploadedFile
>>> import datetime
>>> import time
>>> import re
>>> from decimal import Decimal

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
>>> p.cleaned_data["first_name"], p.cleaned_data["last_name"], p.cleaned_data["birthday"]
(u'John', u'Lennon', datetime.date(1940, 10, 9))
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
>>> p.errors['first_name']
[u'This field is required.']
>>> p.errors['last_name']
[u'This field is required.']
>>> p.errors['birthday']
[u'This field is required.']
>>> p.is_valid()
False
>>> p.cleaned_data
Traceback (most recent call last):
...
AttributeError: 'Person' object has no attribute 'cleaned_data'
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
<ul class="errorlist"><li>This field is required.</li></ul>
<p><label for="id_first_name">First name:</label> <input type="text" name="first_name" id="id_first_name" /></p>
<ul class="errorlist"><li>This field is required.</li></ul>
<p><label for="id_last_name">Last name:</label> <input type="text" name="last_name" id="id_last_name" /></p>
<ul class="errorlist"><li>This field is required.</li></ul>
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
>>> p.cleaned_data
Traceback (most recent call last):
...
AttributeError: 'Person' object has no attribute 'cleaned_data'
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
>>> p.errors['first_name']
[u'This field is required.']
>>> p.errors['birthday']
[u'This field is required.']
>>> p.is_valid()
False
>>> p.errors.as_ul()
u'<ul class="errorlist"><li>first_name<ul class="errorlist"><li>This field is required.</li></ul></li><li>birthday<ul class="errorlist"><li>This field is required.</li></ul></li></ul>'
>>> print p.errors.as_text()
* first_name
  * This field is required.
* birthday
  * This field is required.
>>> p.cleaned_data
Traceback (most recent call last):
...
AttributeError: 'Person' object has no attribute 'cleaned_data'
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

cleaned_data will always *only* contain a key for fields defined in the
Form, even if you pass extra data when you define the Form. In this
example, we pass a bunch of extra fields to the form constructor,
but cleaned_data contains only the form's fields.
>>> data = {'first_name': u'John', 'last_name': u'Lennon', 'birthday': u'1940-10-9', 'extra1': 'hello', 'extra2': 'hello'}
>>> p = Person(data)
>>> p.is_valid()
True
>>> p.cleaned_data['first_name']
u'John'
>>> p.cleaned_data['last_name']
u'Lennon'
>>> p.cleaned_data['birthday']
datetime.date(1940, 10, 9)


cleaned_data will include a key and value for *all* fields defined in the Form,
even if the Form's data didn't include a value for fields that are not
required. In this example, the data dictionary doesn't include a value for the
"nick_name" field, but cleaned_data includes it. For CharFields, it's set to the
empty string.
>>> class OptionalPersonForm(Form):
...     first_name = CharField()
...     last_name = CharField()
...     nick_name = CharField(required=False)
>>> data = {'first_name': u'John', 'last_name': u'Lennon'}
>>> f = OptionalPersonForm(data)
>>> f.is_valid()
True
>>> f.cleaned_data['nick_name']
u''
>>> f.cleaned_data['first_name']
u'John'
>>> f.cleaned_data['last_name']
u'Lennon'

For DateFields, it's set to None.
>>> class OptionalPersonForm(Form):
...     first_name = CharField()
...     last_name = CharField()
...     birth_date = DateField(required=False)
>>> data = {'first_name': u'John', 'last_name': u'Lennon'}
>>> f = OptionalPersonForm(data)
>>> f.is_valid()
True
>>> print f.cleaned_data['birth_date']
None
>>> f.cleaned_data['first_name']
u'John'
>>> f.cleaned_data['last_name']
u'Lennon'

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

'True' or 'true' should be rendered without a value attribute
>>> f = SignupForm({'email': 'test@example.com', 'get_spam': 'True'}, auto_id=False)
>>> print f['get_spam']
<input checked="checked" type="checkbox" name="get_spam" />

>>> f = SignupForm({'email': 'test@example.com', 'get_spam': 'true'}, auto_id=False)
>>> print f['get_spam']
<input checked="checked" type="checkbox" name="get_spam" />

A value of 'False' or 'false' should be rendered unchecked
>>> f = SignupForm({'email': 'test@example.com', 'get_spam': 'False'}, auto_id=False)
>>> print f['get_spam']
<input type="checkbox" name="get_spam" />

>>> f = SignupForm({'email': 'test@example.com', 'get_spam': 'false'}, auto_id=False)
>>> print f['get_spam']
<input type="checkbox" name="get_spam" />

Any Field can have a Widget class passed to its constructor:
>>> class ContactForm(Form):
...     subject = CharField()
...     message = CharField(widget=Textarea)
>>> f = ContactForm(auto_id=False)
>>> print f['subject']
<input type="text" name="subject" />
>>> print f['message']
<textarea rows="10" cols="40" name="message"></textarea>

as_textarea(), as_text() and as_hidden() are shortcuts for changing the output
widget type:
>>> f['subject'].as_textarea()
u'<textarea rows="10" cols="40" name="subject"></textarea>'
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
u'<textarea rows="10" cols="40" name="subject">Hello</textarea>'
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
<li><label for="id_language_0"><input type="radio" id="id_language_0" value="P" name="language" /> Python</label></li>
<li><label for="id_language_1"><input type="radio" id="id_language_1" value="J" name="language" /> Java</label></li>
</ul>

When RadioSelect is used with auto_id, and the whole form is printed using
either as_table() or as_ul(), the label for the RadioSelect will point to the
ID of the *first* radio button.
>>> print f
<tr><th><label for="id_name">Name:</label></th><td><input type="text" name="name" id="id_name" /></td></tr>
<tr><th><label for="id_language_0">Language:</label></th><td><ul>
<li><label for="id_language_0"><input type="radio" id="id_language_0" value="P" name="language" /> Python</label></li>
<li><label for="id_language_1"><input type="radio" id="id_language_1" value="J" name="language" /> Java</label></li>
</ul></td></tr>
>>> print f.as_ul()
<li><label for="id_name">Name:</label> <input type="text" name="name" id="id_name" /></li>
<li><label for="id_language_0">Language:</label> <ul>
<li><label for="id_language_0"><input type="radio" id="id_language_0" value="P" name="language" /> Python</label></li>
<li><label for="id_language_1"><input type="radio" id="id_language_1" value="J" name="language" /> Java</label></li>
</ul></li>
>>> print f.as_p()
<p><label for="id_name">Name:</label> <input type="text" name="name" id="id_name" /></p>
<p><label for="id_language_0">Language:</label> <ul>
<li><label for="id_language_0"><input type="radio" id="id_language_0" value="P" name="language" /> Python</label></li>
<li><label for="id_language_1"><input type="radio" id="id_language_1" value="J" name="language" /> Java</label></li>
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
<li><label for="composers_id_0"><input type="checkbox" name="composers" value="J" id="composers_id_0" /> John Lennon</label></li>
<li><label for="composers_id_1"><input type="checkbox" name="composers" value="P" id="composers_id_1" /> Paul McCartney</label></li>
</ul>

Data for a MultipleChoiceField should be a list. QueryDict, MultiValueDict and
MergeDict (when created as a merge of MultiValueDicts) conveniently work with
this.
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
>>> from django.utils.datastructures import MergeDict
>>> data = MergeDict(MultiValueDict(dict(name=['Yesterday'], composers=['J', 'P'])))
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
>>> f.errors['composers']
[u'This field is required.']
>>> f = SongForm({'name': 'Yesterday', 'composers': ['J']}, auto_id=False)
>>> f.errors
{}
>>> f.cleaned_data['composers']
[u'J']
>>> f.cleaned_data['name']
u'Yesterday'
>>> f = SongForm({'name': 'Yesterday', 'composers': ['J', 'P']}, auto_id=False)
>>> f.errors
{}
>>> f.cleaned_data['composers']
[u'J', u'P']
>>> f.cleaned_data['name']
u'Yesterday'

Validation errors are HTML-escaped when output as HTML.
>>> from django.utils.safestring import mark_safe
>>> class EscapingForm(Form):
...     special_name = CharField(label="<em>Special</em> Field")
...     special_safe_name = CharField(label=mark_safe("<em>Special</em> Field"))
...     def clean_special_name(self):
...         raise ValidationError("Something's wrong with '%s'" % self.cleaned_data['special_name'])
...     def clean_special_safe_name(self):
...         raise ValidationError(mark_safe("'<b>%s</b>' is a safe string" % self.cleaned_data['special_safe_name']))

>>> f = EscapingForm({'special_name': "Nothing to escape", 'special_safe_name': "Nothing to escape"}, auto_id=False)
>>> print f
<tr><th>&lt;em&gt;Special&lt;/em&gt; Field:</th><td><ul class="errorlist"><li>Something&#39;s wrong with &#39;Nothing to escape&#39;</li></ul><input type="text" name="special_name" value="Nothing to escape" /></td></tr>
<tr><th><em>Special</em> Field:</th><td><ul class="errorlist"><li>'<b>Nothing to escape</b>' is a safe string</li></ul><input type="text" name="special_safe_name" value="Nothing to escape" /></td></tr>
>>> f = EscapingForm(
...     {'special_name': "Should escape < & > and <script>alert('xss')</script>",
...     'special_safe_name': "<i>Do not escape</i>"}, auto_id=False)
>>> print f
<tr><th>&lt;em&gt;Special&lt;/em&gt; Field:</th><td><ul class="errorlist"><li>Something&#39;s wrong with &#39;Should escape &lt; &amp; &gt; and &lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;&#39;</li></ul><input type="text" name="special_name" value="Should escape &lt; &amp; &gt; and &lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" /></td></tr>
<tr><th><em>Special</em> Field:</th><td><ul class="errorlist"><li>'<b><i>Do not escape</i></b>' is a safe string</li></ul><input type="text" name="special_safe_name" value="&lt;i&gt;Do not escape&lt;/i&gt;" /></td></tr>

""" + \
r""" # [This concatenation is to keep the string below the jython's 32K limit].
# Validating multiple fields in relation to another ###########################

There are a couple of ways to do multiple-field validation. If you want the
validation message to be associated with a particular field, implement the
clean_XXX() method on the Form, where XXX is the field name. As in
Field.clean(), the clean_XXX() method should return the cleaned value. In the
clean_XXX() method, you have access to self.cleaned_data, which is a dictionary
of all the data that has been cleaned *so far*, in order by the fields,
including the current field (e.g., the field XXX if you're in clean_XXX()).
>>> class UserRegistration(Form):
...    username = CharField(max_length=10)
...    password1 = CharField(widget=PasswordInput)
...    password2 = CharField(widget=PasswordInput)
...    def clean_password2(self):
...        if self.cleaned_data.get('password1') and self.cleaned_data.get('password2') and self.cleaned_data['password1'] != self.cleaned_data['password2']:
...            raise ValidationError(u'Please make sure your passwords match.')
...        return self.cleaned_data['password2']
>>> f = UserRegistration(auto_id=False)
>>> f.errors
{}
>>> f = UserRegistration({}, auto_id=False)
>>> f.errors['username']
[u'This field is required.']
>>> f.errors['password1']
[u'This field is required.']
>>> f.errors['password2']
[u'This field is required.']
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'bar'}, auto_id=False)
>>> f.errors['password2']
[u'Please make sure your passwords match.']
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'foo'}, auto_id=False)
>>> f.errors
{}
>>> f.cleaned_data['username']
u'adrian'
>>> f.cleaned_data['password1']
u'foo'
>>> f.cleaned_data['password2']
u'foo'

Another way of doing multiple-field validation is by implementing the
Form's clean() method. If you do this, any ValidationError raised by that
method will not be associated with a particular field; it will have a
special-case association with the field named '__all__'.
Note that in Form.clean(), you have access to self.cleaned_data, a dictionary of
all the fields/values that have *not* raised a ValidationError. Also note
Form.clean() is required to return a dictionary of all clean data.
>>> class UserRegistration(Form):
...    username = CharField(max_length=10)
...    password1 = CharField(widget=PasswordInput)
...    password2 = CharField(widget=PasswordInput)
...    def clean(self):
...        if self.cleaned_data.get('password1') and self.cleaned_data.get('password2') and self.cleaned_data['password1'] != self.cleaned_data['password2']:
...            raise ValidationError(u'Please make sure your passwords match.')
...        return self.cleaned_data
>>> f = UserRegistration(auto_id=False)
>>> f.errors
{}
>>> f = UserRegistration({}, auto_id=False)
>>> print f.as_table()
<tr><th>Username:</th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="username" maxlength="10" /></td></tr>
<tr><th>Password1:</th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="password" name="password1" /></td></tr>
<tr><th>Password2:</th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="password" name="password2" /></td></tr>
>>> f.errors['username']
[u'This field is required.']
>>> f.errors['password1']
[u'This field is required.']
>>> f.errors['password2']
[u'This field is required.']
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'bar'}, auto_id=False)
>>> f.errors['__all__']
[u'Please make sure your passwords match.']
>>> print f.as_table()
<tr><td colspan="2"><ul class="errorlist"><li>Please make sure your passwords match.</li></ul></td></tr>
<tr><th>Username:</th><td><input type="text" name="username" value="adrian" maxlength="10" /></td></tr>
<tr><th>Password1:</th><td><input type="password" name="password1" /></td></tr>
<tr><th>Password2:</th><td><input type="password" name="password2" /></td></tr>
>>> print f.as_ul()
<li><ul class="errorlist"><li>Please make sure your passwords match.</li></ul></li>
<li>Username: <input type="text" name="username" value="adrian" maxlength="10" /></li>
<li>Password1: <input type="password" name="password1" /></li>
<li>Password2: <input type="password" name="password2" /></li>
>>> f = UserRegistration({'username': 'adrian', 'password1': 'foo', 'password2': 'foo'}, auto_id=False)
>>> f.errors
{}
>>> f.cleaned_data['username']
u'adrian'
>>> f.cleaned_data['password1']
u'foo'
>>> f.cleaned_data['password2']
u'foo'

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
...         Form.__init__(self, data, auto_id=auto_id)
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
...         Form.__init__(self, data, auto_id=auto_id)
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
...             self.fields['first_name'].widget.attrs['class'] = 'required'
...             self.fields['last_name'].required = True
...             self.fields['last_name'].widget.attrs['class'] = 'required'
>>> f = Person(names_required=False)
>>> f['first_name'].field.required, f['last_name'].field.required
(False, False)
>>> f['first_name'].field.widget.attrs, f['last_name'].field.widget.attrs
({}, {})
>>> f = Person(names_required=True)
>>> f['first_name'].field.required, f['last_name'].field.required
(True, True)
>>> f['first_name'].field.widget.attrs, f['last_name'].field.widget.attrs
({'class': 'required'}, {'class': 'required'})
>>> f = Person(names_required=False)
>>> f['first_name'].field.required, f['last_name'].field.required
(False, False)
>>> f['first_name'].field.widget.attrs, f['last_name'].field.widget.attrs
({}, {})
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
<ul class="errorlist"><li>(Hidden field hidden_text) This field is required.</li></ul>
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

Labels for as_* methods will only end in a colon if they don't end in other
punctuation already.
>>> class Questions(Form):
...    q1 = CharField(label='The first question')
...    q2 = CharField(label='What is your name?')
...    q3 = CharField(label='The answer to life is:')
...    q4 = CharField(label='Answer this question!')
...    q5 = CharField(label='The last question. Period.')
>>> print Questions(auto_id=False).as_p()
<p>The first question: <input type="text" name="q1" /></p>
<p>What is your name? <input type="text" name="q2" /></p>
<p>The answer to life is: <input type="text" name="q3" /></p>
<p>Answer this question! <input type="text" name="q4" /></p>
<p>The last question. Period. <input type="text" name="q5" /></p>
>>> print Questions().as_p()
<p><label for="id_q1">The first question:</label> <input type="text" name="q1" id="id_q1" /></p>
<p><label for="id_q2">What is your name?</label> <input type="text" name="q2" id="id_q2" /></p>
<p><label for="id_q3">The answer to life is:</label> <input type="text" name="q3" id="id_q3" /></p>
<p><label for="id_q4">Answer this question!</label> <input type="text" name="q4" id="id_q4" /></p>
<p><label for="id_q5">The last question. Period.</label> <input type="text" name="q5" id="id_q5" /></p>

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


# Label Suffix ################################################################

You can specify the 'label_suffix' argument to a Form class to modify the
punctuation symbol used at the end of a label.  By default, the colon (:) is
used, and is only appended to the label if the label doesn't already end with a
punctuation symbol: ., !, ? or :.  If you specify a different suffix, it will
be appended regardless of the last character of the label.

>>> class FavoriteForm(Form):
...     color = CharField(label='Favorite color?')
...     animal = CharField(label='Favorite animal')
...
>>> f = FavoriteForm(auto_id=False)
>>> print f.as_ul()
<li>Favorite color? <input type="text" name="color" /></li>
<li>Favorite animal: <input type="text" name="animal" /></li>
>>> f = FavoriteForm(auto_id=False, label_suffix='?')
>>> print f.as_ul()
<li>Favorite color? <input type="text" name="color" /></li>
<li>Favorite animal? <input type="text" name="animal" /></li>
>>> f = FavoriteForm(auto_id=False, label_suffix='')
>>> print f.as_ul()
<li>Favorite color? <input type="text" name="color" /></li>
<li>Favorite animal <input type="text" name="animal" /></li>
>>> f = FavoriteForm(auto_id=False, label_suffix=u'\u2192')
>>> f.as_ul()
u'<li>Favorite color? <input type="text" name="color" /></li>\n<li>Favorite animal\u2192 <input type="text" name="animal" /></li>'

""" + \
r""" # [This concatenation is to keep the string below the jython's 32K limit].

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
>>> p.errors['username']
[u'This field is required.']
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
>>> p.errors['username']
[u'This field is required.']
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

# Callable initial data ########################################################

The previous technique dealt with raw values as initial data, but it's also
possible to specify callable data.

>>> class UserRegistration(Form):
...    username = CharField(max_length=10)
...    password = CharField(widget=PasswordInput)
...    options = MultipleChoiceField(choices=[('f','foo'),('b','bar'),('w','whiz')])

We need to define functions that get called later.
>>> def initial_django():
...     return 'django'
>>> def initial_stephane():
...     return 'stephane'
>>> def initial_options():
...     return ['f','b']
>>> def initial_other_options():
...     return ['b','w']


Here, we're not submitting any data, so the initial value will be displayed.
>>> p = UserRegistration(initial={'username': initial_django, 'options': initial_options}, auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" value="django" maxlength="10" /></li>
<li>Password: <input type="password" name="password" /></li>
<li>Options: <select multiple="multiple" name="options">
<option value="f" selected="selected">foo</option>
<option value="b" selected="selected">bar</option>
<option value="w">whiz</option>
</select></li>

The 'initial' parameter is meaningless if you pass data.
>>> p = UserRegistration({}, initial={'username': initial_django, 'options': initial_options}, auto_id=False)
>>> print p.as_ul()
<li><ul class="errorlist"><li>This field is required.</li></ul>Username: <input type="text" name="username" maxlength="10" /></li>
<li><ul class="errorlist"><li>This field is required.</li></ul>Password: <input type="password" name="password" /></li>
<li><ul class="errorlist"><li>This field is required.</li></ul>Options: <select multiple="multiple" name="options">
<option value="f">foo</option>
<option value="b">bar</option>
<option value="w">whiz</option>
</select></li>
>>> p = UserRegistration({'username': u''}, initial={'username': initial_django}, auto_id=False)
>>> print p.as_ul()
<li><ul class="errorlist"><li>This field is required.</li></ul>Username: <input type="text" name="username" maxlength="10" /></li>
<li><ul class="errorlist"><li>This field is required.</li></ul>Password: <input type="password" name="password" /></li>
<li><ul class="errorlist"><li>This field is required.</li></ul>Options: <select multiple="multiple" name="options">
<option value="f">foo</option>
<option value="b">bar</option>
<option value="w">whiz</option>
</select></li>
>>> p = UserRegistration({'username': u'foo', 'options':['f','b']}, initial={'username': initial_django}, auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" value="foo" maxlength="10" /></li>
<li><ul class="errorlist"><li>This field is required.</li></ul>Password: <input type="password" name="password" /></li>
<li>Options: <select multiple="multiple" name="options">
<option value="f" selected="selected">foo</option>
<option value="b" selected="selected">bar</option>
<option value="w">whiz</option>
</select></li>

A callable 'initial' value is *not* used as a fallback if data is not provided.
In this example, we don't provide a value for 'username', and the form raises a
validation error rather than using the initial value for 'username'.
>>> p = UserRegistration({'password': 'secret'}, initial={'username': initial_django, 'options': initial_options})
>>> p.errors['username']
[u'This field is required.']
>>> p.is_valid()
False

If a Form defines 'initial' *and* 'initial' is passed as a parameter to Form(),
then the latter will get precedence.
>>> class UserRegistration(Form):
...    username = CharField(max_length=10, initial=initial_django)
...    password = CharField(widget=PasswordInput)
...    options = MultipleChoiceField(choices=[('f','foo'),('b','bar'),('w','whiz')], initial=initial_other_options)

>>> p = UserRegistration(auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" value="django" maxlength="10" /></li>
<li>Password: <input type="password" name="password" /></li>
<li>Options: <select multiple="multiple" name="options">
<option value="f">foo</option>
<option value="b" selected="selected">bar</option>
<option value="w" selected="selected">whiz</option>
</select></li>
>>> p = UserRegistration(initial={'username': initial_stephane, 'options': initial_options}, auto_id=False)
>>> print p.as_ul()
<li>Username: <input type="text" name="username" value="stephane" maxlength="10" /></li>
<li>Password: <input type="password" name="password" /></li>
<li>Options: <select multiple="multiple" name="options">
<option value="f" selected="selected">foo</option>
<option value="b" selected="selected">bar</option>
<option value="w">whiz</option>
</select></li>

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
>>> p.cleaned_data['first_name']
u'John'
>>> p.cleaned_data['last_name']
u'Lennon'
>>> p.cleaned_data['birthday']
datetime.date(1940, 10, 9)

Let's try submitting some bad data to make sure form.errors and field.errors
work as expected.
>>> data = {
...     'person1-first_name': u'',
...     'person1-last_name': u'',
...     'person1-birthday': u''
... }
>>> p = Person(data, prefix='person1')
>>> p.errors['first_name']
[u'This field is required.']
>>> p.errors['last_name']
[u'This field is required.']
>>> p.errors['birthday']
[u'This field is required.']
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
>>> p.errors['first_name']
[u'This field is required.']
>>> p.errors['last_name']
[u'This field is required.']
>>> p.errors['birthday']
[u'This field is required.']

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
>>> p1.cleaned_data['first_name']
u'John'
>>> p1.cleaned_data['last_name']
u'Lennon'
>>> p1.cleaned_data['birthday']
datetime.date(1940, 10, 9)
>>> p2 = Person(data, prefix='person2')
>>> p2.is_valid()
True
>>> p2.cleaned_data['first_name']
u'Jim'
>>> p2.cleaned_data['last_name']
u'Morrison'
>>> p2.cleaned_data['birthday']
datetime.date(1943, 12, 8)

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
>>> p.cleaned_data['first_name']
u'John'
>>> p.cleaned_data['last_name']
u'Lennon'
>>> p.cleaned_data['birthday']
datetime.date(1940, 10, 9)

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

# Forms with FileFields ################################################

FileFields are a special case because they take their data from the request.FILES,
not request.POST.

>>> class FileForm(Form):
...     file1 = FileField()
>>> f = FileForm(auto_id=False)
>>> print f
<tr><th>File1:</th><td><input type="file" name="file1" /></td></tr>

>>> f = FileForm(data={}, files={}, auto_id=False)
>>> print f
<tr><th>File1:</th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="file" name="file1" /></td></tr>

>>> f = FileForm(data={}, files={'file1': SimpleUploadedFile('name', '')}, auto_id=False)
>>> print f
<tr><th>File1:</th><td><ul class="errorlist"><li>The submitted file is empty.</li></ul><input type="file" name="file1" /></td></tr>

>>> f = FileForm(data={}, files={'file1': 'something that is not a file'}, auto_id=False)
>>> print f
<tr><th>File1:</th><td><ul class="errorlist"><li>No file was submitted. Check the encoding type on the form.</li></ul><input type="file" name="file1" /></td></tr>

>>> f = FileForm(data={}, files={'file1': SimpleUploadedFile('name', 'some content')}, auto_id=False)
>>> print f
<tr><th>File1:</th><td><input type="file" name="file1" /></td></tr>
>>> f.is_valid()
True

>>> f = FileForm(data={}, files={'file1': SimpleUploadedFile('我隻氣墊船裝滿晒鱔.txt', 'मेरी मँडराने वाली नाव सर्पमीनों से भरी ह')}, auto_id=False)
>>> print f
<tr><th>File1:</th><td><input type="file" name="file1" /></td></tr>

# Basic form processing in a view #############################################

>>> from django.template import Template, Context
>>> class UserRegistration(Form):
...    username = CharField(max_length=10)
...    password1 = CharField(widget=PasswordInput)
...    password2 = CharField(widget=PasswordInput)
...    def clean(self):
...        if self.cleaned_data.get('password1') and self.cleaned_data.get('password2') and self.cleaned_data['password1'] != self.cleaned_data['password2']:
...            raise ValidationError(u'Please make sure your passwords match.')
...        return self.cleaned_data
>>> def my_function(method, post_data):
...     if method == 'POST':
...         form = UserRegistration(post_data, auto_id=False)
...     else:
...         form = UserRegistration(auto_id=False)
...     if form.is_valid():
...         return 'VALID: %r' % form.cleaned_data
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
<tr><th>Username:</th><td><ul class="errorlist"><li>Ensure this value has at most 10 characters (it has 23).</li></ul><input type="text" name="username" value="this-is-a-long-username" maxlength="10" /></td></tr>
<tr><th>Password1:</th><td><input type="password" name="password1" /></td></tr>
<tr><th>Password2:</th><td><input type="password" name="password2" /></td></tr>
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
...        if self.cleaned_data.get('password1') and self.cleaned_data.get('password2') and self.cleaned_data['password1'] != self.cleaned_data['password2']:
...            raise ValidationError(u'Please make sure your passwords match.')
...        return self.cleaned_data

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
<p>Username: <input type="text" name="username" maxlength="10" /><br />Good luck picking a username that doesn&#39;t already exist.</p>
<p>Password1: <input type="password" name="password1" /></p>
<p>Password2: <input type="password" name="password2" /></p>
<input type="submit" />
</form>
>>> Template('{{ form.password1.help_text }}').render(Context({'form': UserRegistration(auto_id=False)}))
u''

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
<p><label>Password: <input type="password" name="password1" /></label></p>
<p><label>Password (again): <input type="password" name="password2" /></label></p>
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
<p><label>Password: <input type="password" name="password1" /></label></p>
<p><label>Password (again): <input type="password" name="password2" /></label></p>
<input type="submit" />
</form>


# The empty_permitted attribute ##############################################

Sometimes (pretty much in formsets) we want to allow a form to pass validation
if it is completely empty. We can accomplish this by using the empty_permitted
agrument to a form constructor.

>>> class SongForm(Form):
...     artist = CharField()
...     name = CharField()

First let's show what happens id empty_permitted=False (the default):

>>> data = {'artist': '', 'song': ''}

>>> form = SongForm(data, empty_permitted=False)
>>> form.is_valid()
False
>>> form.errors
{'name': [u'This field is required.'], 'artist': [u'This field is required.']}
>>> form.cleaned_data
Traceback (most recent call last):
...
AttributeError: 'SongForm' object has no attribute 'cleaned_data'


Now let's show what happens when empty_permitted=True and the form is empty.

>>> form = SongForm(data, empty_permitted=True)
>>> form.is_valid()
True
>>> form.errors
{}
>>> form.cleaned_data
{}

But if we fill in data for one of the fields, the form is no longer empty and
the whole thing must pass validation.

>>> data = {'artist': 'The Doors', 'song': ''}
>>> form = SongForm(data, empty_permitted=False)
>>> form.is_valid()
False
>>> form.errors
{'name': [u'This field is required.']}
>>> form.cleaned_data
Traceback (most recent call last):
...
AttributeError: 'SongForm' object has no attribute 'cleaned_data'

If a field is not given in the data then None is returned for its data. Lets
make sure that when checking for empty_permitted that None is treated
accordingly.

>>> data = {'artist': None, 'song': ''}
>>> form = SongForm(data, empty_permitted=True)
>>> form.is_valid()
True

However, we *really* need to be sure we are checking for None as any data in
initial that returns False on a boolean call needs to be treated literally.

>>> class PriceForm(Form):
...     amount = FloatField()
...     qty = IntegerField()

>>> data = {'amount': '0.0', 'qty': ''}
>>> form = PriceForm(data, initial={'amount': 0.0}, empty_permitted=True)
>>> form.is_valid()
True

# Extracting hidden and visible fields ######################################

>>> class SongForm(Form):
...     token = CharField(widget=HiddenInput)
...     artist = CharField()
...     name = CharField()
>>> form = SongForm()
>>> [f.name for f in form.hidden_fields()]
['token']
>>> [f.name for f in form.visible_fields()]
['artist', 'name']

# Hidden initial input gets its own unique id ################################

>>> class MyForm(Form):
...     field1 = CharField(max_length=50, show_hidden_initial=True)
>>> print MyForm()
<tr><th><label for="id_field1">Field1:</label></th><td><input id="id_field1" type="text" name="field1" maxlength="50" /><input type="hidden" name="initial-field1" id="initial-id_field1" /></td></tr>

# The error_html_class and required_html_class attributes ####################

>>> class Person(Form):
...     name = CharField()
...     is_cool = NullBooleanField()
...     email = EmailField(required=False)
...     age = IntegerField()

>>> p = Person({})
>>> p.error_css_class = 'error'
>>> p.required_css_class = 'required'

>>> print p.as_ul()
<li class="required error"><ul class="errorlist"><li>This field is required.</li></ul><label for="id_name">Name:</label> <input type="text" name="name" id="id_name" /></li>
<li class="required"><label for="id_is_cool">Is cool:</label> <select name="is_cool" id="id_is_cool">
<option value="1" selected="selected">Unknown</option>
<option value="2">Yes</option>
<option value="3">No</option>
</select></li>
<li><label for="id_email">Email:</label> <input type="text" name="email" id="id_email" /></li>
<li class="required error"><ul class="errorlist"><li>This field is required.</li></ul><label for="id_age">Age:</label> <input type="text" name="age" id="id_age" /></li>

>>> print p.as_p()
<ul class="errorlist"><li>This field is required.</li></ul>
<p class="required error"><label for="id_name">Name:</label> <input type="text" name="name" id="id_name" /></p>
<p class="required"><label for="id_is_cool">Is cool:</label> <select name="is_cool" id="id_is_cool">
<option value="1" selected="selected">Unknown</option>
<option value="2">Yes</option>
<option value="3">No</option>
</select></p>
<p><label for="id_email">Email:</label> <input type="text" name="email" id="id_email" /></p>
<ul class="errorlist"><li>This field is required.</li></ul>
<p class="required error"><label for="id_age">Age:</label> <input type="text" name="age" id="id_age" /></p>

>>> print p.as_table()
<tr class="required error"><th><label for="id_name">Name:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="name" id="id_name" /></td></tr>
<tr class="required"><th><label for="id_is_cool">Is cool:</label></th><td><select name="is_cool" id="id_is_cool">
<option value="1" selected="selected">Unknown</option>
<option value="2">Yes</option>
<option value="3">No</option>
</select></td></tr>
<tr><th><label for="id_email">Email:</label></th><td><input type="text" name="email" id="id_email" /></td></tr>
<tr class="required error"><th><label for="id_age">Age:</label></th><td><ul class="errorlist"><li>This field is required.</li></ul><input type="text" name="age" id="id_age" /></td></tr>



# Checking that the label for SplitDateTimeField is not being displayed #####

>>> class EventForm(Form):
...     happened_at = SplitDateTimeField(widget=widgets.SplitHiddenDateTimeWidget)
...
>>> form = EventForm()
>>> form.as_ul()
u'<input type="hidden" name="happened_at_0" id="id_happened_at_0" /><input type="hidden" name="happened_at_1" id="id_happened_at_1" />'

"""
