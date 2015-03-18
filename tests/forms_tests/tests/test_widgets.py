# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import datetime

from django.contrib.admin.tests import AdminSeleniumWebDriverTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.forms import (
    BooleanField, CheckboxInput, CheckboxSelectMultiple, ChoiceField,
    ClearableFileInput, DateInput, DateTimeField, DateTimeInput, FileInput,
    Form, HiddenInput, MultipleHiddenInput, MultiWidget, NullBooleanSelect,
    PasswordInput, RadioSelect, Select, SelectMultiple, SplitDateTimeWidget,
    Textarea, TextInput, TimeInput,
)
from django.forms.widgets import (
    ChoiceFieldRenderer, ChoiceInput, RadioFieldRenderer,
)
from django.test import TestCase, ignore_warnings, override_settings
from django.utils import six
from django.utils.deprecation import RemovedInDjango19Warning
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.safestring import SafeData, mark_safe
from django.utils.translation import activate, deactivate, override

from ..models import Article


class FormsWidgetTestCase(TestCase):
    # Each Widget class corresponds to an HTML form widget. A Widget knows how to
    # render itself, given a field name and some data. Widgets don't perform
    # validation.
    def test_textinput(self):
        w = TextInput()
        self.assertHTMLEqual(w.render('email', ''), '<input type="text" name="email" />')
        self.assertHTMLEqual(w.render('email', None), '<input type="text" name="email" />')
        self.assertHTMLEqual(w.render('email', 'test@example.com'), '<input type="text" name="email" value="test@example.com" />')
        self.assertHTMLEqual(w.render('email', 'some "quoted" & ampersanded value'), '<input type="text" name="email" value="some &quot;quoted&quot; &amp; ampersanded value" />')
        self.assertHTMLEqual(w.render('email', 'test@example.com', attrs={'class': 'fun'}), '<input type="text" name="email" value="test@example.com" class="fun" />')

        self.assertHTMLEqual(w.render('email', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'}), '<input type="text" name="email" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" class="fun" />')

        # You can also pass 'attrs' to the constructor:
        w = TextInput(attrs={'class': 'fun', 'type': 'email'})
        self.assertHTMLEqual(w.render('email', ''), '<input type="email" class="fun" name="email" />')
        self.assertHTMLEqual(w.render('email', 'foo@example.com'), '<input type="email" class="fun" value="foo@example.com" name="email" />')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = TextInput(attrs={'class': 'pretty'})
        self.assertHTMLEqual(w.render('email', '', attrs={'class': 'special'}), '<input type="text" class="special" name="email" />')

        # 'attrs' can be safe-strings if needed)
        w = TextInput(attrs={'onBlur': mark_safe("function('foo')")})
        self.assertHTMLEqual(w.render('email', ''), '<input onBlur="function(\'foo\')" type="text" name="email" />')

    def test_passwordinput(self):
        w = PasswordInput()
        self.assertHTMLEqual(w.render('email', ''), '<input type="password" name="email" />')
        self.assertHTMLEqual(w.render('email', None), '<input type="password" name="email" />')
        self.assertHTMLEqual(w.render('email', 'secret'), '<input type="password" name="email" />')

        # The render_value argument lets you specify whether the widget should render
        # its value. For security reasons, this is off by default.
        w = PasswordInput(render_value=True)
        self.assertHTMLEqual(w.render('email', ''), '<input type="password" name="email" />')
        self.assertHTMLEqual(w.render('email', None), '<input type="password" name="email" />')
        self.assertHTMLEqual(w.render('email', 'test@example.com'), '<input type="password" name="email" value="test@example.com" />')
        self.assertHTMLEqual(w.render('email', 'some "quoted" & ampersanded value'), '<input type="password" name="email" value="some &quot;quoted&quot; &amp; ampersanded value" />')
        self.assertHTMLEqual(w.render('email', 'test@example.com', attrs={'class': 'fun'}), '<input type="password" name="email" value="test@example.com" class="fun" />')

        # You can also pass 'attrs' to the constructor:
        w = PasswordInput(attrs={'class': 'fun'}, render_value=True)
        self.assertHTMLEqual(w.render('email', ''), '<input type="password" class="fun" name="email" />')
        self.assertHTMLEqual(w.render('email', 'foo@example.com'), '<input type="password" class="fun" value="foo@example.com" name="email" />')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = PasswordInput(attrs={'class': 'pretty'}, render_value=True)
        self.assertHTMLEqual(w.render('email', '', attrs={'class': 'special'}), '<input type="password" class="special" name="email" />')

        self.assertHTMLEqual(w.render('email', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'}), '<input type="password" class="fun" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" name="email" />')

    def test_hiddeninput(self):
        w = HiddenInput()
        self.assertHTMLEqual(w.render('email', ''), '<input type="hidden" name="email" />')
        self.assertHTMLEqual(w.render('email', None), '<input type="hidden" name="email" />')
        self.assertHTMLEqual(w.render('email', 'test@example.com'), '<input type="hidden" name="email" value="test@example.com" />')
        self.assertHTMLEqual(w.render('email', 'some "quoted" & ampersanded value'), '<input type="hidden" name="email" value="some &quot;quoted&quot; &amp; ampersanded value" />')
        self.assertHTMLEqual(w.render('email', 'test@example.com', attrs={'class': 'fun'}), '<input type="hidden" name="email" value="test@example.com" class="fun" />')

        # You can also pass 'attrs' to the constructor:
        w = HiddenInput(attrs={'class': 'fun'})
        self.assertHTMLEqual(w.render('email', ''), '<input type="hidden" class="fun" name="email" />')
        self.assertHTMLEqual(w.render('email', 'foo@example.com'), '<input type="hidden" class="fun" value="foo@example.com" name="email" />')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = HiddenInput(attrs={'class': 'pretty'})
        self.assertHTMLEqual(w.render('email', '', attrs={'class': 'special'}), '<input type="hidden" class="special" name="email" />')

        self.assertHTMLEqual(w.render('email', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'}), '<input type="hidden" class="fun" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" name="email" />')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = HiddenInput(attrs={'class': 'pretty'})
        self.assertHTMLEqual(w.render('email', '', attrs={'class': 'special'}), '<input type="hidden" class="special" name="email" />')

        # Boolean values are rendered to their string forms ("True" and "False").
        w = HiddenInput()
        self.assertHTMLEqual(w.render('get_spam', False), '<input type="hidden" name="get_spam" value="False" />')
        self.assertHTMLEqual(w.render('get_spam', True), '<input type="hidden" name="get_spam" value="True" />')

    def test_multiplehiddeninput(self):
        w = MultipleHiddenInput()
        self.assertHTMLEqual(w.render('email', []), '')
        self.assertHTMLEqual(w.render('email', None), '')
        self.assertHTMLEqual(w.render('email', ['test@example.com']), '<input type="hidden" name="email" value="test@example.com" />')
        self.assertHTMLEqual(w.render('email', ['some "quoted" & ampersanded value']), '<input type="hidden" name="email" value="some &quot;quoted&quot; &amp; ampersanded value" />')
        self.assertHTMLEqual(w.render('email', ['test@example.com', 'foo@example.com']), '<input type="hidden" name="email" value="test@example.com" />\n<input type="hidden" name="email" value="foo@example.com" />')
        self.assertHTMLEqual(w.render('email', ['test@example.com'], attrs={'class': 'fun'}), '<input type="hidden" name="email" value="test@example.com" class="fun" />')
        self.assertHTMLEqual(w.render('email', ['test@example.com', 'foo@example.com'], attrs={'class': 'fun'}), '<input type="hidden" name="email" value="test@example.com" class="fun" />\n<input type="hidden" name="email" value="foo@example.com" class="fun" />')

        # You can also pass 'attrs' to the constructor:
        w = MultipleHiddenInput(attrs={'class': 'fun'})
        self.assertHTMLEqual(w.render('email', []), '')
        self.assertHTMLEqual(w.render('email', ['foo@example.com']), '<input type="hidden" class="fun" value="foo@example.com" name="email" />')
        self.assertHTMLEqual(w.render('email', ['foo@example.com', 'test@example.com']), '<input type="hidden" class="fun" value="foo@example.com" name="email" />\n<input type="hidden" class="fun" value="test@example.com" name="email" />')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = MultipleHiddenInput(attrs={'class': 'pretty'})
        self.assertHTMLEqual(w.render('email', ['foo@example.com'], attrs={'class': 'special'}), '<input type="hidden" class="special" value="foo@example.com" name="email" />')

        self.assertHTMLEqual(w.render('email', ['ŠĐĆŽćžšđ'], attrs={'class': 'fun'}), '<input type="hidden" class="fun" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" name="email" />')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = MultipleHiddenInput(attrs={'class': 'pretty'})
        self.assertHTMLEqual(w.render('email', ['foo@example.com'], attrs={'class': 'special'}), '<input type="hidden" class="special" value="foo@example.com" name="email" />')

        # Each input gets a separate ID.
        w = MultipleHiddenInput()
        self.assertHTMLEqual(w.render('letters', list('abc'), attrs={'id': 'hideme'}), '<input type="hidden" name="letters" value="a" id="hideme_0" />\n<input type="hidden" name="letters" value="b" id="hideme_1" />\n<input type="hidden" name="letters" value="c" id="hideme_2" />')

    def test_fileinput(self):
        # FileInput widgets don't ever show the value, because the old value is of no use
        # if you are updating the form or if the provided file generated an error.
        w = FileInput()
        self.assertHTMLEqual(w.render('email', ''), '<input type="file" name="email" />')
        self.assertHTMLEqual(w.render('email', None), '<input type="file" name="email" />')
        self.assertHTMLEqual(w.render('email', 'test@example.com'), '<input type="file" name="email" />')
        self.assertHTMLEqual(w.render('email', 'some "quoted" & ampersanded value'), '<input type="file" name="email" />')
        self.assertHTMLEqual(w.render('email', 'test@example.com', attrs={'class': 'fun'}), '<input type="file" name="email" class="fun" />')

        # You can also pass 'attrs' to the constructor:
        w = FileInput(attrs={'class': 'fun'})
        self.assertHTMLEqual(w.render('email', ''), '<input type="file" class="fun" name="email" />')
        self.assertHTMLEqual(w.render('email', 'foo@example.com'), '<input type="file" class="fun" name="email" />')

        self.assertHTMLEqual(w.render('email', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'}), '<input type="file" class="fun" name="email" />')

    def test_textarea(self):
        w = Textarea()
        self.assertHTMLEqual(w.render('msg', ''), '<textarea rows="10" cols="40" name="msg"></textarea>')
        self.assertHTMLEqual(w.render('msg', None), '<textarea rows="10" cols="40" name="msg"></textarea>')
        self.assertHTMLEqual(w.render('msg', 'value'), '<textarea rows="10" cols="40" name="msg">value</textarea>')
        self.assertHTMLEqual(w.render('msg', 'some "quoted" & ampersanded value'), '<textarea rows="10" cols="40" name="msg">some &quot;quoted&quot; &amp; ampersanded value</textarea>')
        self.assertHTMLEqual(w.render('msg', mark_safe('pre &quot;quoted&quot; value')), '<textarea rows="10" cols="40" name="msg">pre &quot;quoted&quot; value</textarea>')
        self.assertHTMLEqual(w.render('msg', 'value', attrs={'class': 'pretty', 'rows': 20}), '<textarea class="pretty" rows="20" cols="40" name="msg">value</textarea>')

        # You can also pass 'attrs' to the constructor:
        w = Textarea(attrs={'class': 'pretty'})
        self.assertHTMLEqual(w.render('msg', ''), '<textarea rows="10" cols="40" name="msg" class="pretty"></textarea>')
        self.assertHTMLEqual(w.render('msg', 'example'), '<textarea rows="10" cols="40" name="msg" class="pretty">example</textarea>')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = Textarea(attrs={'class': 'pretty'})
        self.assertHTMLEqual(w.render('msg', '', attrs={'class': 'special'}), '<textarea rows="10" cols="40" name="msg" class="special"></textarea>')

        self.assertHTMLEqual(w.render('msg', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'}), '<textarea rows="10" cols="40" name="msg" class="fun">\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111</textarea>')

    def test_checkboxinput(self):
        w = CheckboxInput()
        self.assertHTMLEqual(w.render('is_cool', ''), '<input type="checkbox" name="is_cool" />')
        self.assertHTMLEqual(w.render('is_cool', None), '<input type="checkbox" name="is_cool" />')
        self.assertHTMLEqual(w.render('is_cool', False), '<input type="checkbox" name="is_cool" />')
        self.assertHTMLEqual(w.render('is_cool', True), '<input checked="checked" type="checkbox" name="is_cool" />')

        # Using any value that's not in ('', None, False, True) will check the checkbox
        # and set the 'value' attribute.
        self.assertHTMLEqual(w.render('is_cool', 'foo'), '<input checked="checked" type="checkbox" name="is_cool" value="foo" />')

        self.assertHTMLEqual(w.render('is_cool', False, attrs={'class': 'pretty'}), '<input type="checkbox" name="is_cool" class="pretty" />')

        # regression for #17114
        self.assertHTMLEqual(w.render('is_cool', 0), '<input checked="checked" type="checkbox" name="is_cool" value="0" />')
        self.assertHTMLEqual(w.render('is_cool', 1), '<input checked="checked" type="checkbox" name="is_cool" value="1" />')

        # You can also pass 'attrs' to the constructor:
        w = CheckboxInput(attrs={'class': 'pretty'})
        self.assertHTMLEqual(w.render('is_cool', ''), '<input type="checkbox" class="pretty" name="is_cool" />')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = CheckboxInput(attrs={'class': 'pretty'})
        self.assertHTMLEqual(w.render('is_cool', '', attrs={'class': 'special'}), '<input type="checkbox" class="special" name="is_cool" />')

        # You can pass 'check_test' to the constructor. This is a callable that takes the
        # value and returns True if the box should be checked.
        w = CheckboxInput(check_test=lambda value: value.startswith('hello'))
        self.assertHTMLEqual(w.render('greeting', ''), '<input type="checkbox" name="greeting" />')
        self.assertHTMLEqual(w.render('greeting', 'hello'), '<input checked="checked" type="checkbox" name="greeting" value="hello" />')
        self.assertHTMLEqual(w.render('greeting', 'hello there'), '<input checked="checked" type="checkbox" name="greeting" value="hello there" />')
        self.assertHTMLEqual(w.render('greeting', 'hello & goodbye'), '<input checked="checked" type="checkbox" name="greeting" value="hello &amp; goodbye" />')

        # Ticket #17888: calling check_test shouldn't swallow exceptions
        with self.assertRaises(AttributeError):
            w.render('greeting', True)

        # The CheckboxInput widget will return False if the key is not found in the data
        # dictionary (because HTML form submission doesn't send any result for unchecked
        # checkboxes).
        self.assertFalse(w.value_from_datadict({}, {}, 'testing'))

        value = w.value_from_datadict({'testing': '0'}, {}, 'testing')
        self.assertIsInstance(value, bool)
        self.assertTrue(value)

    def test_select(self):
        w = Select()
        self.assertHTMLEqual(w.render('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select name="beatle">
<option value="J" selected="selected">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>""")

        # If the value is None, none of the options are selected:
        self.assertHTMLEqual(w.render('beatle', None, choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select name="beatle">
<option value="J">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>""")

        # If the value corresponds to a label (but not to an option value), none of the options are selected:
        self.assertHTMLEqual(w.render('beatle', 'John', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select name="beatle">
<option value="J">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>""")

        # Only one option can be selected, see #8103:
        self.assertHTMLEqual(w.render('choices', '0', choices=(('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('0', 'extra'))), """<select name="choices">
<option value="0" selected="selected">0</option>
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="0">extra</option>
</select>""")

        # The value is compared to its str():
        self.assertHTMLEqual(w.render('num', 2, choices=[('1', '1'), ('2', '2'), ('3', '3')]), """<select name="num">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")
        self.assertHTMLEqual(w.render('num', '2', choices=[(1, 1), (2, 2), (3, 3)]), """<select name="num">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")
        self.assertHTMLEqual(w.render('num', 2, choices=[(1, 1), (2, 2), (3, 3)]), """<select name="num">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")

        # The 'choices' argument can be any iterable:
        from itertools import chain

        def get_choices():
            for i in range(5):
                yield (i, i)
        self.assertHTMLEqual(w.render('num', 2, choices=get_choices()), """<select name="num">
<option value="0">0</option>
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
<option value="4">4</option>
</select>""")
        things = ({'id': 1, 'name': 'And Boom'}, {'id': 2, 'name': 'One More Thing!'})

        class SomeForm(Form):
            somechoice = ChoiceField(choices=chain((('', '-' * 9),), [(thing['id'], thing['name']) for thing in things]))
        f = SomeForm()
        self.assertHTMLEqual(f.as_table(), '<tr><th><label for="id_somechoice">Somechoice:</label></th><td><select name="somechoice" id="id_somechoice">\n<option value="" selected="selected">---------</option>\n<option value="1">And Boom</option>\n<option value="2">One More Thing!</option>\n</select></td></tr>')
        self.assertHTMLEqual(f.as_table(), '<tr><th><label for="id_somechoice">Somechoice:</label></th><td><select name="somechoice" id="id_somechoice">\n<option value="" selected="selected">---------</option>\n<option value="1">And Boom</option>\n<option value="2">One More Thing!</option>\n</select></td></tr>')
        f = SomeForm({'somechoice': 2})
        self.assertHTMLEqual(f.as_table(), '<tr><th><label for="id_somechoice">Somechoice:</label></th><td><select name="somechoice" id="id_somechoice">\n<option value="">---------</option>\n<option value="1">And Boom</option>\n<option value="2" selected="selected">One More Thing!</option>\n</select></td></tr>')

        # You can also pass 'choices' to the constructor:
        w = Select(choices=[(1, 1), (2, 2), (3, 3)])
        self.assertHTMLEqual(w.render('num', 2), """<select name="num">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")

        # If 'choices' is passed to both the constructor and render(), then they'll both be in the output:
        self.assertHTMLEqual(w.render('num', 2, choices=[(4, 4), (5, 5)]), """<select name="num">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
<option value="4">4</option>
<option value="5">5</option>
</select>""")

        # Choices are escaped correctly
        self.assertHTMLEqual(w.render('escape', None, choices=(('bad', 'you & me'), ('good', mark_safe('you &gt; me')))), """<select name="escape">
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="bad">you &amp; me</option>
<option value="good">you &gt; me</option>
</select>""")

        # Unicode choices are correctly rendered as HTML
        self.assertHTMLEqual(w.render('email', 'ŠĐĆŽćžšđ', choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')]), '<select name="email">\n<option value="1">1</option>\n<option value="2">2</option>\n<option value="3">3</option>\n<option value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" selected="selected">\u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111</option>\n<option value="\u0107\u017e\u0161\u0111">abc\u0107\u017e\u0161\u0111</option>\n</select>')

        # If choices is passed to the constructor and is a generator, it can be iterated
        # over multiple times without getting consumed:
        w = Select(choices=get_choices())
        self.assertHTMLEqual(w.render('num', 2), """<select name="num">
<option value="0">0</option>
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
<option value="4">4</option>
</select>""")
        self.assertHTMLEqual(w.render('num', 3), """<select name="num">
<option value="0">0</option>
<option value="1">1</option>
<option value="2">2</option>
<option value="3" selected="selected">3</option>
<option value="4">4</option>
</select>""")

        # Choices can be nested one level in order to create HTML optgroups:
        w.choices = (
            ('outer1', 'Outer 1'),
            ('Group "1"', (('inner1', 'Inner 1'), ('inner2', 'Inner 2'))),
        )
        self.assertHTMLEqual(w.render('nestchoice', None), """<select name="nestchoice">
<option value="outer1">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>""")

        self.assertHTMLEqual(w.render('nestchoice', 'outer1'), """<select name="nestchoice">
<option value="outer1" selected="selected">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>""")

        self.assertHTMLEqual(w.render('nestchoice', 'inner1'), """<select name="nestchoice">
<option value="outer1">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1" selected="selected">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>""")

    def test_nullbooleanselect(self):
        w = NullBooleanSelect()
        self.assertTrue(w.render('is_cool', True), """<select name="is_cool">
<option value="1">Unknown</option>
<option value="2" selected="selected">Yes</option>
<option value="3">No</option>
</select>""")
        self.assertHTMLEqual(w.render('is_cool', False), """<select name="is_cool">
<option value="1">Unknown</option>
<option value="2">Yes</option>
<option value="3" selected="selected">No</option>
</select>""")
        self.assertHTMLEqual(w.render('is_cool', None), """<select name="is_cool">
<option value="1" selected="selected">Unknown</option>
<option value="2">Yes</option>
<option value="3">No</option>
</select>""")
        self.assertHTMLEqual(w.render('is_cool', '2'), """<select name="is_cool">
<option value="1">Unknown</option>
<option value="2" selected="selected">Yes</option>
<option value="3">No</option>
</select>""")
        self.assertHTMLEqual(w.render('is_cool', '3'), """<select name="is_cool">
<option value="1">Unknown</option>
<option value="2">Yes</option>
<option value="3" selected="selected">No</option>
</select>""")

    def test_selectmultiple(self):
        w = SelectMultiple()
        self.assertHTMLEqual(w.render('beatles', ['J'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select multiple="multiple" name="beatles">
<option value="J" selected="selected">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>""")
        self.assertHTMLEqual(w.render('beatles', ['J', 'P'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select multiple="multiple" name="beatles">
<option value="J" selected="selected">John</option>
<option value="P" selected="selected">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>""")
        self.assertHTMLEqual(w.render('beatles', ['J', 'P', 'R'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select multiple="multiple" name="beatles">
<option value="J" selected="selected">John</option>
<option value="P" selected="selected">Paul</option>
<option value="G">George</option>
<option value="R" selected="selected">Ringo</option>
</select>""")

        # If the value is None, none of the options are selected:
        self.assertHTMLEqual(w.render('beatles', None, choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select multiple="multiple" name="beatles">
<option value="J">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>""")

        # If the value corresponds to a label (but not to an option value), none of the options are selected:
        self.assertHTMLEqual(w.render('beatles', ['John'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select multiple="multiple" name="beatles">
<option value="J">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>""")

        # Multiple options (with the same value) can be selected, see #8103:
        self.assertHTMLEqual(w.render('choices', ['0'], choices=(('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('0', 'extra'))), """<select multiple="multiple" name="choices">
<option value="0" selected="selected">0</option>
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="0" selected="selected">extra</option>
</select>""")

        # If multiple values are given, but some of them are not valid, the valid ones are selected:
        self.assertHTMLEqual(w.render('beatles', ['J', 'G', 'foo'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select multiple="multiple" name="beatles">
<option value="J" selected="selected">John</option>
<option value="P">Paul</option>
<option value="G" selected="selected">George</option>
<option value="R">Ringo</option>
</select>""")

        # The value is compared to its str():
        self.assertHTMLEqual(w.render('nums', [2], choices=[('1', '1'), ('2', '2'), ('3', '3')]), """<select multiple="multiple" name="nums">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")
        self.assertHTMLEqual(w.render('nums', ['2'], choices=[(1, 1), (2, 2), (3, 3)]), """<select multiple="multiple" name="nums">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")
        self.assertHTMLEqual(w.render('nums', [2], choices=[(1, 1), (2, 2), (3, 3)]), """<select multiple="multiple" name="nums">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")

        # The 'choices' argument can be any iterable:
        def get_choices():
            for i in range(5):
                yield (i, i)
        self.assertHTMLEqual(w.render('nums', [2], choices=get_choices()), """<select multiple="multiple" name="nums">
<option value="0">0</option>
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
<option value="4">4</option>
</select>""")

        # You can also pass 'choices' to the constructor:
        w = SelectMultiple(choices=[(1, 1), (2, 2), (3, 3)])
        self.assertHTMLEqual(w.render('nums', [2]), """<select multiple="multiple" name="nums">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")

        # If 'choices' is passed to both the constructor and render(), then they'll both be in the output:
        self.assertHTMLEqual(w.render('nums', [2], choices=[(4, 4), (5, 5)]), """<select multiple="multiple" name="nums">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
<option value="4">4</option>
<option value="5">5</option>
</select>""")

        # Choices are escaped correctly
        self.assertHTMLEqual(w.render('escape', None, choices=(('bad', 'you & me'), ('good', mark_safe('you &gt; me')))), """<select multiple="multiple" name="escape">
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="bad">you &amp; me</option>
<option value="good">you &gt; me</option>
</select>""")

        # Unicode choices are correctly rendered as HTML
        self.assertHTMLEqual(w.render('nums', ['ŠĐĆŽćžšđ'], choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')]), '<select multiple="multiple" name="nums">\n<option value="1">1</option>\n<option value="2">2</option>\n<option value="3">3</option>\n<option value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" selected="selected">\u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111</option>\n<option value="\u0107\u017e\u0161\u0111">abc\u0107\u017e\u0161\u0111</option>\n</select>')

        # Choices can be nested one level in order to create HTML optgroups:
        w.choices = (('outer1', 'Outer 1'), ('Group "1"', (('inner1', 'Inner 1'), ('inner2', 'Inner 2'))))
        self.assertHTMLEqual(w.render('nestchoice', None), """<select multiple="multiple" name="nestchoice">
<option value="outer1">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>""")

        self.assertHTMLEqual(w.render('nestchoice', ['outer1']), """<select multiple="multiple" name="nestchoice">
<option value="outer1" selected="selected">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>""")

        self.assertHTMLEqual(w.render('nestchoice', ['inner1']), """<select multiple="multiple" name="nestchoice">
<option value="outer1">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1" selected="selected">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>""")

        self.assertHTMLEqual(w.render('nestchoice', ['outer1', 'inner2']), """<select multiple="multiple" name="nestchoice">
<option value="outer1" selected="selected">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1">Inner 1</option>
<option value="inner2" selected="selected">Inner 2</option>
</optgroup>
</select>""")

    def test_radioselect(self):
        w = RadioSelect()
        self.assertHTMLEqual(w.render('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input checked="checked" type="radio" name="beatle" value="J" /> John</label></li>
<li><label><input type="radio" name="beatle" value="P" /> Paul</label></li>
<li><label><input type="radio" name="beatle" value="G" /> George</label></li>
<li><label><input type="radio" name="beatle" value="R" /> Ringo</label></li>
</ul>""")

        # If the value is None, none of the options are checked:
        self.assertHTMLEqual(w.render('beatle', None, choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input type="radio" name="beatle" value="J" /> John</label></li>
<li><label><input type="radio" name="beatle" value="P" /> Paul</label></li>
<li><label><input type="radio" name="beatle" value="G" /> George</label></li>
<li><label><input type="radio" name="beatle" value="R" /> Ringo</label></li>
</ul>""")

        # If the value corresponds to a label (but not to an option value), none of the options are checked:
        self.assertHTMLEqual(w.render('beatle', 'John', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input type="radio" name="beatle" value="J" /> John</label></li>
<li><label><input type="radio" name="beatle" value="P" /> Paul</label></li>
<li><label><input type="radio" name="beatle" value="G" /> George</label></li>
<li><label><input type="radio" name="beatle" value="R" /> Ringo</label></li>
</ul>""")

        # The value is compared to its str():
        self.assertHTMLEqual(w.render('num', 2, choices=[('1', '1'), ('2', '2'), ('3', '3')]), """<ul>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
</ul>""")
        self.assertHTMLEqual(w.render('num', '2', choices=[(1, 1), (2, 2), (3, 3)]), """<ul>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
</ul>""")
        self.assertHTMLEqual(w.render('num', 2, choices=[(1, 1), (2, 2), (3, 3)]), """<ul>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
</ul>""")

        # The 'choices' argument can be any iterable:
        def get_choices():
            for i in range(5):
                yield (i, i)
        self.assertHTMLEqual(w.render('num', 2, choices=get_choices()), """<ul>
<li><label><input type="radio" name="num" value="0" /> 0</label></li>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
<li><label><input type="radio" name="num" value="4" /> 4</label></li>
</ul>""")

        # You can also pass 'choices' to the constructor:
        w = RadioSelect(choices=[(1, 1), (2, 2), (3, 3)])
        self.assertHTMLEqual(w.render('num', 2), """<ul>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
</ul>""")

        # If 'choices' is passed to both the constructor and render(), then they'll both be in the output:
        self.assertHTMLEqual(w.render('num', 2, choices=[(4, 4), (5, 5)]), """<ul>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
<li><label><input type="radio" name="num" value="4" /> 4</label></li>
<li><label><input type="radio" name="num" value="5" /> 5</label></li>
</ul>""")

        # Choices are escaped correctly
        w = RadioSelect()
        self.assertHTMLEqual(w.render('escape', None, choices=(('bad', 'you & me'), ('good', mark_safe('you &gt; me')))), """<ul>
<li><label><input type="radio" name="escape" value="bad" /> you &amp; me</label></li>
<li><label><input type="radio" name="escape" value="good" /> you &gt; me</label></li>
</ul>""")

        # Unicode choices are correctly rendered as HTML
        w = RadioSelect()
        self.assertHTMLEqual(six.text_type(w.render('email', 'ŠĐĆŽćžšđ', choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')])), '<ul>\n<li><label><input checked="checked" type="radio" name="email" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" /> \u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111</label></li>\n<li><label><input type="radio" name="email" value="\u0107\u017e\u0161\u0111" /> abc\u0107\u017e\u0161\u0111</label></li>\n</ul>')

        # Attributes provided at instantiation are passed to the constituent inputs
        w = RadioSelect(attrs={'id': 'foo'})
        self.assertHTMLEqual(w.render('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul id="foo">
<li><label for="foo_0"><input checked="checked" type="radio" id="foo_0" value="J" name="beatle" /> John</label></li>
<li><label for="foo_1"><input type="radio" id="foo_1" value="P" name="beatle" /> Paul</label></li>
<li><label for="foo_2"><input type="radio" id="foo_2" value="G" name="beatle" /> George</label></li>
<li><label for="foo_3"><input type="radio" id="foo_3" value="R" name="beatle" /> Ringo</label></li>
</ul>""")

        # Attributes provided at render-time are passed to the constituent inputs
        w = RadioSelect()
        self.assertHTMLEqual(w.render('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')), attrs={'id': 'bar'}), """<ul id="bar">
<li><label for="bar_0"><input checked="checked" type="radio" id="bar_0" value="J" name="beatle" /> John</label></li>
<li><label for="bar_1"><input type="radio" id="bar_1" value="P" name="beatle" /> Paul</label></li>
<li><label for="bar_2"><input type="radio" id="bar_2" value="G" name="beatle" /> George</label></li>
<li><label for="bar_3"><input type="radio" id="bar_3" value="R" name="beatle" /> Ringo</label></li>
</ul>""")

    def test_radiofieldrenderer(self):
        # RadioSelect uses a RadioFieldRenderer to render the individual radio inputs.
        # You can manipulate that object directly to customize the way the RadioSelect
        # is rendered.
        w = RadioSelect()
        r = w.get_renderer('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
        inp_set1 = []
        inp_set2 = []
        inp_set3 = []
        inp_set4 = []

        for inp in r:
            inp_set1.append(str(inp))
            inp_set2.append('%s<br />' % inp)
            inp_set3.append('<p>%s %s</p>' % (inp.tag(), inp.choice_label))
            inp_set4.append('%s %s %s %s %s' % (inp.name, inp.value, inp.choice_value, inp.choice_label, inp.is_checked()))

        self.assertHTMLEqual('\n'.join(inp_set1), """<label><input checked="checked" type="radio" name="beatle" value="J" /> John</label>
<label><input type="radio" name="beatle" value="P" /> Paul</label>
<label><input type="radio" name="beatle" value="G" /> George</label>
<label><input type="radio" name="beatle" value="R" /> Ringo</label>""")
        self.assertHTMLEqual('\n'.join(inp_set2), """<label><input checked="checked" type="radio" name="beatle" value="J" /> John</label><br />
<label><input type="radio" name="beatle" value="P" /> Paul</label><br />
<label><input type="radio" name="beatle" value="G" /> George</label><br />
<label><input type="radio" name="beatle" value="R" /> Ringo</label><br />""")
        self.assertHTMLEqual('\n'.join(inp_set3), """<p><input checked="checked" type="radio" name="beatle" value="J" /> John</p>
<p><input type="radio" name="beatle" value="P" /> Paul</p>
<p><input type="radio" name="beatle" value="G" /> George</p>
<p><input type="radio" name="beatle" value="R" /> Ringo</p>""")
        self.assertHTMLEqual('\n'.join(inp_set4), """beatle J J John True
beatle J P Paul False
beatle J G George False
beatle J R Ringo False""")

        # A RadioFieldRenderer object also allows index access to individual RadioChoiceInput
        w = RadioSelect()
        r = w.get_renderer('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
        self.assertHTMLEqual(str(r[1]), '<label><input type="radio" name="beatle" value="P" /> Paul</label>')
        self.assertHTMLEqual(str(r[0]), '<label><input checked="checked" type="radio" name="beatle" value="J" /> John</label>')
        self.assertTrue(r[0].is_checked())
        self.assertFalse(r[1].is_checked())
        self.assertEqual((r[1].name, r[1].value, r[1].choice_value, r[1].choice_label), ('beatle', 'J', 'P', 'Paul'))

        # These individual widgets can accept extra attributes if manually rendered.
        self.assertHTMLEqual(
            r[1].render(attrs={'extra': 'value'}),
            '<label><input type="radio" extra="value" name="beatle" value="P" /> Paul</label>'
        )

        with self.assertRaises(IndexError):
            r[10]

        # You can create your own custom renderers for RadioSelect to use.
        class MyRenderer(RadioFieldRenderer):
            def render(self):
                return '<br />\n'.join(six.text_type(choice) for choice in self)
        w = RadioSelect(renderer=MyRenderer)
        self.assertHTMLEqual(w.render('beatle', 'G', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<label><input type="radio" name="beatle" value="J" /> John</label><br />
<label><input type="radio" name="beatle" value="P" /> Paul</label><br />
<label><input checked="checked" type="radio" name="beatle" value="G" /> George</label><br />
<label><input type="radio" name="beatle" value="R" /> Ringo</label>""")

        # Or you can use custom RadioSelect fields that use your custom renderer.
        class CustomRadioSelect(RadioSelect):
            renderer = MyRenderer
        w = CustomRadioSelect()
        self.assertHTMLEqual(w.render('beatle', 'G', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<label><input type="radio" name="beatle" value="J" /> John</label><br />
<label><input type="radio" name="beatle" value="P" /> Paul</label><br />
<label><input checked="checked" type="radio" name="beatle" value="G" /> George</label><br />
<label><input type="radio" name="beatle" value="R" /> Ringo</label>""")

        # You can customize rendering with outer_html/inner_html renderer variables (#22950)
        class MyRenderer(RadioFieldRenderer):
            outer_html = str('<div{id_attr}>{content}</div>')  # str is just to test some Python 2 issue with bytestrings
            inner_html = '<p>{choice_value}{sub_widgets}</p>'
        w = RadioSelect(renderer=MyRenderer)
        output = w.render('beatle', 'J',
                          choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')),
                          attrs={'id': 'bar'})
        self.assertIsInstance(output, SafeData)
        self.assertHTMLEqual(output, """<div id="bar">
<p><label for="bar_0"><input checked="checked" type="radio" id="bar_0" value="J" name="beatle" /> John</label></p>
<p><label for="bar_1"><input type="radio" id="bar_1" value="P" name="beatle" /> Paul</label></p>
<p><label for="bar_2"><input type="radio" id="bar_2" value="G" name="beatle" /> George</label></p>
<p><label for="bar_3"><input type="radio" id="bar_3" value="R" name="beatle" /> Ringo</label></p>
</div>""")

    def test_nested_choices(self):
        # Choices can be nested for radio buttons:
        w = RadioSelect()
        w.choices = (
            ('unknown', 'Unknown'),
            ('Audio', (('vinyl', 'Vinyl'), ('cd', 'CD'))),
            ('Video', (('vhs', 'VHS'), ('dvd', 'DVD'))),
        )
        self.assertHTMLEqual(w.render('nestchoice', 'dvd', attrs={'id': 'media'}), """<ul id="media">
<li><label for="media_0"><input id="media_0" name="nestchoice" type="radio" value="unknown" /> Unknown</label></li>
<li>Audio<ul id="media_1">
<li><label for="media_1_0"><input id="media_1_0" name="nestchoice" type="radio" value="vinyl" /> Vinyl</label></li>
<li><label for="media_1_1"><input id="media_1_1" name="nestchoice" type="radio" value="cd" /> CD</label></li>
</ul></li>
<li>Video<ul id="media_2">
<li><label for="media_2_0"><input id="media_2_0" name="nestchoice" type="radio" value="vhs" /> VHS</label></li>
<li><label for="media_2_1"><input checked="checked" id="media_2_1" name="nestchoice" type="radio" value="dvd" /> DVD</label></li>
</ul></li>
</ul>""")

        # Choices can be nested for checkboxes:
        w = CheckboxSelectMultiple()
        w.choices = (
            ('unknown', 'Unknown'),
            ('Audio', (('vinyl', 'Vinyl'), ('cd', 'CD'))),
            ('Video', (('vhs', 'VHS'), ('dvd', 'DVD'))),
        )
        self.assertHTMLEqual(w.render('nestchoice', ('vinyl', 'dvd'), attrs={'id': 'media'}), """<ul id="media">
<li><label for="media_0"><input id="media_0" name="nestchoice" type="checkbox" value="unknown" /> Unknown</label></li>
<li>Audio<ul id="media_1">
<li><label for="media_1_0"><input checked="checked" id="media_1_0" name="nestchoice" type="checkbox" value="vinyl" /> Vinyl</label></li>
<li><label for="media_1_1"><input id="media_1_1" name="nestchoice" type="checkbox" value="cd" /> CD</label></li>
</ul></li>
<li>Video<ul id="media_2">
<li><label for="media_2_0"><input id="media_2_0" name="nestchoice" type="checkbox" value="vhs" /> VHS</label></li>
<li><label for="media_2_1"><input checked="checked" id="media_2_1" name="nestchoice" type="checkbox" value="dvd" /> DVD</label></li>
</ul></li>
</ul>""")

    def test_checkboxselectmultiple(self):
        w = CheckboxSelectMultiple()
        self.assertHTMLEqual(w.render('beatles', ['J'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input checked="checked" type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>""")
        self.assertHTMLEqual(w.render('beatles', ['J', 'P'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input checked="checked" type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input checked="checked" type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>""")
        self.assertHTMLEqual(w.render('beatles', ['J', 'P', 'R'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input checked="checked" type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input checked="checked" type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input checked="checked" type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>""")

        # If the value is None, none of the options are selected:
        self.assertHTMLEqual(w.render('beatles', None, choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>""")

        # If the value corresponds to a label (but not to an option value), none of the options are selected:
        self.assertHTMLEqual(w.render('beatles', ['John'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>""")

        # If multiple values are given, but some of them are not valid, the valid ones are selected:
        self.assertHTMLEqual(w.render('beatles', ['J', 'G', 'foo'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input checked="checked" type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input checked="checked" type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>""")

        # The value is compared to its str():
        self.assertHTMLEqual(w.render('nums', [2], choices=[('1', '1'), ('2', '2'), ('3', '3')]), """<ul>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
</ul>""")
        self.assertHTMLEqual(w.render('nums', ['2'], choices=[(1, 1), (2, 2), (3, 3)]), """<ul>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
</ul>""")
        self.assertHTMLEqual(w.render('nums', [2], choices=[(1, 1), (2, 2), (3, 3)]), """<ul>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
</ul>""")

        # The 'choices' argument can be any iterable:
        def get_choices():
            for i in range(5):
                yield (i, i)
        self.assertHTMLEqual(w.render('nums', [2], choices=get_choices()), """<ul>
<li><label><input type="checkbox" name="nums" value="0" /> 0</label></li>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
<li><label><input type="checkbox" name="nums" value="4" /> 4</label></li>
</ul>""")

        # You can also pass 'choices' to the constructor:
        w = CheckboxSelectMultiple(choices=[(1, 1), (2, 2), (3, 3)])
        self.assertHTMLEqual(w.render('nums', [2]), """<ul>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
</ul>""")

        # If 'choices' is passed to both the constructor and render(), then they'll both be in the output:
        self.assertHTMLEqual(w.render('nums', [2], choices=[(4, 4), (5, 5)]), """<ul>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
<li><label><input type="checkbox" name="nums" value="4" /> 4</label></li>
<li><label><input type="checkbox" name="nums" value="5" /> 5</label></li>
</ul>""")

        # Choices are escaped correctly
        self.assertHTMLEqual(w.render('escape', None, choices=(('bad', 'you & me'), ('good', mark_safe('you &gt; me')))), """<ul>
<li><label><input type="checkbox" name="escape" value="1" /> 1</label></li>
<li><label><input type="checkbox" name="escape" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="escape" value="3" /> 3</label></li>
<li><label><input type="checkbox" name="escape" value="bad" /> you &amp; me</label></li>
<li><label><input type="checkbox" name="escape" value="good" /> you &gt; me</label></li>
</ul>""")

        # Unicode choices are correctly rendered as HTML
        self.assertHTMLEqual(w.render('nums', ['ŠĐĆŽćžšđ'], choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')]), '<ul>\n<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>\n<li><label><input type="checkbox" name="nums" value="2" /> 2</label></li>\n<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>\n<li><label><input checked="checked" type="checkbox" name="nums" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" /> \u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111</label></li>\n<li><label><input type="checkbox" name="nums" value="\u0107\u017e\u0161\u0111" /> abc\u0107\u017e\u0161\u0111</label></li>\n</ul>')

        # Each input gets a separate ID
        self.assertHTMLEqual(CheckboxSelectMultiple().render('letters', list('ac'), choices=zip(list('abc'), list('ABC')), attrs={'id': 'abc'}), """<ul id="abc">
<li><label for="abc_0"><input checked="checked" type="checkbox" name="letters" value="a" id="abc_0" /> A</label></li>
<li><label for="abc_1"><input type="checkbox" name="letters" value="b" id="abc_1" /> B</label></li>
<li><label for="abc_2"><input checked="checked" type="checkbox" name="letters" value="c" id="abc_2" /> C</label></li>
</ul>""")

        # Each input gets a separate ID when the ID is passed to the constructor
        self.assertHTMLEqual(CheckboxSelectMultiple(attrs={'id': 'abc'}).render('letters', list('ac'), choices=zip(list('abc'), list('ABC'))), """<ul id="abc">
<li><label for="abc_0"><input checked="checked" type="checkbox" name="letters" value="a" id="abc_0" /> A</label></li>
<li><label for="abc_1"><input type="checkbox" name="letters" value="b" id="abc_1" /> B</label></li>
<li><label for="abc_2"><input checked="checked" type="checkbox" name="letters" value="c" id="abc_2" /> C</label></li>
</ul>""")

        w = CheckboxSelectMultiple()
        r = w.get_renderer('abc', 'b', choices=[(c, c.upper()) for c in 'abc'])
        # You can iterate over the CheckboxFieldRenderer to get individual elements
        expected = [
            '<label><input type="checkbox" name="abc" value="a" /> A</label>',
            '<label><input checked="checked" type="checkbox" name="abc" value="b" /> B</label>',
            '<label><input type="checkbox" name="abc" value="c" /> C</label>',
        ]
        for output, expected in zip(r, expected):
            self.assertHTMLEqual(force_text(output), expected)

        # You can access individual elements
        self.assertHTMLEqual(force_text(r[1]),
            '<label><input checked="checked" type="checkbox" name="abc" value="b" /> B</label>')

        # Out-of-range errors are propagated
        with self.assertRaises(IndexError):
            r[42]

    def test_subwidget(self):
        # Each subwidget tag gets a separate ID when the widget has an ID specified
        self.assertHTMLEqual("\n".join(c.tag() for c in CheckboxSelectMultiple(attrs={'id': 'abc'}).subwidgets('letters', list('ac'), choices=zip(list('abc'), list('ABC')))), """<input checked="checked" type="checkbox" name="letters" value="a" id="abc_0" />
<input type="checkbox" name="letters" value="b" id="abc_1" />
<input checked="checked" type="checkbox" name="letters" value="c" id="abc_2" />""")

        # Each subwidget tag does not get an ID if the widget does not have an ID specified
        self.assertHTMLEqual("\n".join(c.tag() for c in CheckboxSelectMultiple().subwidgets('letters', list('ac'), choices=zip(list('abc'), list('ABC')))), """<input checked="checked" type="checkbox" name="letters" value="a" />
<input type="checkbox" name="letters" value="b" />
<input checked="checked" type="checkbox" name="letters" value="c" />""")

        # The id_for_label property of the subwidget should return the ID that is used on the subwidget's tag
        self.assertHTMLEqual("\n".join('<input type="checkbox" name="letters" value="%s" id="%s" />' % (c.choice_value, c.id_for_label) for c in CheckboxSelectMultiple(attrs={'id': 'abc'}).subwidgets('letters', [], choices=zip(list('abc'), list('ABC')))), """<input type="checkbox" name="letters" value="a" id="abc_0" />
<input type="checkbox" name="letters" value="b" id="abc_1" />
<input type="checkbox" name="letters" value="c" id="abc_2" />""")

    def test_multi(self):
        class MyMultiWidget(MultiWidget):
            def decompress(self, value):
                if value:
                    return value.split('__')
                return ['', '']

            def format_output(self, rendered_widgets):
                return '<br />'.join(rendered_widgets)

        w = MyMultiWidget(widgets=(TextInput(attrs={'class': 'big'}), TextInput(attrs={'class': 'small'})))
        self.assertHTMLEqual(w.render('name', ['john', 'lennon']), '<input type="text" class="big" value="john" name="name_0" /><br /><input type="text" class="small" value="lennon" name="name_1" />')
        self.assertHTMLEqual(w.render('name', 'john__lennon'), '<input type="text" class="big" value="john" name="name_0" /><br /><input type="text" class="small" value="lennon" name="name_1" />')
        self.assertHTMLEqual(w.render('name', 'john__lennon', attrs={'id': 'foo'}), '<input id="foo_0" type="text" class="big" value="john" name="name_0" /><br /><input id="foo_1" type="text" class="small" value="lennon" name="name_1" />')
        w = MyMultiWidget(widgets=(TextInput(attrs={'class': 'big'}), TextInput(attrs={'class': 'small'})), attrs={'id': 'bar'})
        self.assertHTMLEqual(w.render('name', ['john', 'lennon']), '<input id="bar_0" type="text" class="big" value="john" name="name_0" /><br /><input id="bar_1" type="text" class="small" value="lennon" name="name_1" />')

        # Test needs_multipart_form=True if any widget needs it
        w = MyMultiWidget(widgets=(TextInput(), FileInput()))
        self.assertTrue(w.needs_multipart_form)

        # Test needs_multipart_form=False if no widget needs it
        w = MyMultiWidget(widgets=(TextInput(), TextInput()))
        self.assertFalse(w.needs_multipart_form)

    def test_splitdatetime(self):
        w = SplitDateTimeWidget()
        self.assertHTMLEqual(w.render('date', ''), '<input type="text" name="date_0" /><input type="text" name="date_1" />')
        self.assertHTMLEqual(w.render('date', None), '<input type="text" name="date_0" /><input type="text" name="date_1" />')
        self.assertHTMLEqual(w.render('date', datetime.datetime(2006, 1, 10, 7, 30)), '<input type="text" name="date_0" value="2006-01-10" /><input type="text" name="date_1" value="07:30:00" />')
        self.assertHTMLEqual(w.render('date', [datetime.date(2006, 1, 10), datetime.time(7, 30)]), '<input type="text" name="date_0" value="2006-01-10" /><input type="text" name="date_1" value="07:30:00" />')

        # You can also pass 'attrs' to the constructor. In this case, the attrs will be
        w = SplitDateTimeWidget(attrs={'class': 'pretty'})
        self.assertHTMLEqual(w.render('date', datetime.datetime(2006, 1, 10, 7, 30)), '<input type="text" class="pretty" value="2006-01-10" name="date_0" /><input type="text" class="pretty" value="07:30:00" name="date_1" />')

        # Use 'date_format' and 'time_format' to change the way a value is displayed.
        w = SplitDateTimeWidget(date_format='%d/%m/%Y', time_format='%H:%M')
        self.assertHTMLEqual(w.render('date', datetime.datetime(2006, 1, 10, 7, 30)), '<input type="text" name="date_0" value="10/01/2006" /><input type="text" name="date_1" value="07:30" />')

    def test_datetimeinput(self):
        w = DateTimeInput()
        self.assertHTMLEqual(w.render('date', None), '<input type="text" name="date" />')
        d = datetime.datetime(2007, 9, 17, 12, 51, 34, 482548)
        self.assertEqual(str(d), '2007-09-17 12:51:34.482548')

        # The microseconds are trimmed on display, by default.
        self.assertHTMLEqual(w.render('date', d), '<input type="text" name="date" value="2007-09-17 12:51:34" />')
        self.assertHTMLEqual(w.render('date', datetime.datetime(2007, 9, 17, 12, 51, 34)), '<input type="text" name="date" value="2007-09-17 12:51:34" />')
        self.assertHTMLEqual(w.render('date', datetime.datetime(2007, 9, 17, 12, 51)), '<input type="text" name="date" value="2007-09-17 12:51:00" />')

        # Use 'format' to change the way a value is displayed.
        w = DateTimeInput(format='%d/%m/%Y %H:%M', attrs={'type': 'datetime'})
        self.assertHTMLEqual(w.render('date', d), '<input type="datetime" name="date" value="17/09/2007 12:51" />')

    def test_dateinput(self):
        w = DateInput()
        self.assertHTMLEqual(w.render('date', None), '<input type="text" name="date" />')
        d = datetime.date(2007, 9, 17)
        self.assertEqual(str(d), '2007-09-17')

        self.assertHTMLEqual(w.render('date', d), '<input type="text" name="date" value="2007-09-17" />')
        self.assertHTMLEqual(w.render('date', datetime.date(2007, 9, 17)), '<input type="text" name="date" value="2007-09-17" />')

        # We should be able to initialize from a unicode value.
        self.assertHTMLEqual(w.render('date', '2007-09-17'), '<input type="text" name="date" value="2007-09-17" />')

        # Use 'format' to change the way a value is displayed.
        w = DateInput(format='%d/%m/%Y', attrs={'type': 'date'})
        self.assertHTMLEqual(w.render('date', d), '<input type="date" name="date" value="17/09/2007" />')

    def test_timeinput(self):
        w = TimeInput()
        self.assertHTMLEqual(w.render('time', None), '<input type="text" name="time" />')
        t = datetime.time(12, 51, 34, 482548)
        self.assertEqual(str(t), '12:51:34.482548')

        # The microseconds are trimmed on display, by default.
        self.assertHTMLEqual(w.render('time', t), '<input type="text" name="time" value="12:51:34" />')
        self.assertHTMLEqual(w.render('time', datetime.time(12, 51, 34)), '<input type="text" name="time" value="12:51:34" />')
        self.assertHTMLEqual(w.render('time', datetime.time(12, 51)), '<input type="text" name="time" value="12:51:00" />')

        # We should be able to initialize from a unicode value.
        self.assertHTMLEqual(w.render('time', '13:12:11'), '<input type="text" name="time" value="13:12:11" />')

        # Use 'format' to change the way a value is displayed.
        w = TimeInput(format='%H:%M', attrs={'type': 'time'})
        self.assertHTMLEqual(w.render('time', t), '<input type="time" name="time" value="12:51" />')

    def test_splithiddendatetime(self):
        from django.forms.widgets import SplitHiddenDateTimeWidget

        w = SplitHiddenDateTimeWidget()
        self.assertHTMLEqual(w.render('date', ''), '<input type="hidden" name="date_0" /><input type="hidden" name="date_1" />')
        d = datetime.datetime(2007, 9, 17, 12, 51, 34, 482548)
        self.assertHTMLEqual(str(d), '2007-09-17 12:51:34.482548')
        self.assertHTMLEqual(w.render('date', d), '<input type="hidden" name="date_0" value="2007-09-17" /><input type="hidden" name="date_1" value="12:51:34" />')
        self.assertHTMLEqual(w.render('date', datetime.datetime(2007, 9, 17, 12, 51, 34)), '<input type="hidden" name="date_0" value="2007-09-17" /><input type="hidden" name="date_1" value="12:51:34" />')
        self.assertHTMLEqual(w.render('date', datetime.datetime(2007, 9, 17, 12, 51)), '<input type="hidden" name="date_0" value="2007-09-17" /><input type="hidden" name="date_1" value="12:51:00" />')

    def test_sub_widget_html_safe(self):
        widget = TextInput()
        subwidget = next(widget.subwidgets('username', 'John Doe'))
        self.assertTrue(hasattr(subwidget, '__html__'))
        self.assertEqual(force_text(subwidget), subwidget.__html__())

    def test_choice_input_html_safe(self):
        widget = ChoiceInput('choices', 'CHOICE1', {}, ('CHOICE1', 'first choice'), 0)
        self.assertTrue(hasattr(ChoiceInput, '__html__'))
        self.assertEqual(force_text(widget), widget.__html__())

    def test_choice_field_renderer_html_safe(self):
        renderer = ChoiceFieldRenderer('choices', 'CHOICE1', {}, [('CHOICE1', 'first_choice')])
        renderer.choice_input_class = lambda *args: args
        self.assertTrue(hasattr(ChoiceFieldRenderer, '__html__'))
        self.assertEqual(force_text(renderer), renderer.__html__())


class NullBooleanSelectLazyForm(Form):
    """Form to test for lazy evaluation. Refs #17190"""
    bool = BooleanField(widget=NullBooleanSelect())


@override_settings(USE_L10N=True)
class FormsI18NWidgetsTestCase(TestCase):
    def setUp(self):
        super(FormsI18NWidgetsTestCase, self).setUp()
        activate('de-at')

    def tearDown(self):
        deactivate()
        super(FormsI18NWidgetsTestCase, self).tearDown()

    def test_datetimeinput(self):
        w = DateTimeInput()
        d = datetime.datetime(2007, 9, 17, 12, 51, 34, 482548)
        self.assertHTMLEqual(w.render('date', d), '<input type="text" name="date" value="17.09.2007 12:51:34" />')

    def test_dateinput(self):
        w = DateInput()
        d = datetime.date(2007, 9, 17)
        self.assertHTMLEqual(w.render('date', d), '<input type="text" name="date" value="17.09.2007" />')

    def test_timeinput(self):
        w = TimeInput()
        t = datetime.time(12, 51, 34, 482548)
        self.assertHTMLEqual(w.render('time', t), '<input type="text" name="time" value="12:51:34" />')

    def test_datetime_locale_aware(self):
        w = DateTimeInput()
        d = datetime.datetime(2007, 9, 17, 12, 51, 34, 482548)
        with self.settings(USE_L10N=False):
            self.assertHTMLEqual(w.render('date', d), '<input type="text" name="date" value="2007-09-17 12:51:34" />')
        with override('es'):
            self.assertHTMLEqual(w.render('date', d), '<input type="text" name="date" value="17/09/2007 12:51:34" />')

    def test_splithiddendatetime(self):
        from django.forms.widgets import SplitHiddenDateTimeWidget

        w = SplitHiddenDateTimeWidget()
        self.assertHTMLEqual(w.render('date', datetime.datetime(2007, 9, 17, 12, 51)), '<input type="hidden" name="date_0" value="17.09.2007" /><input type="hidden" name="date_1" value="12:51:00" />')

    def test_nullbooleanselect(self):
        """
        Ensure that the NullBooleanSelect widget's options are lazily
        localized.
        Refs #17190
        """
        f = NullBooleanSelectLazyForm()
        self.assertHTMLEqual(f.fields['bool'].widget.render('id_bool', True), '<select name="id_bool">\n<option value="1">Unbekannt</option>\n<option value="2" selected="selected">Ja</option>\n<option value="3">Nein</option>\n</select>')


class SelectAndTextWidget(MultiWidget):
    """
    MultiWidget subclass
    """
    def __init__(self, choices=[]):
        widgets = [
            RadioSelect(choices=choices),
            TextInput
        ]
        super(SelectAndTextWidget, self).__init__(widgets)

    def _set_choices(self, choices):
        """
        When choices are set for this widget, we want to pass those along to the Select widget
        """
        self.widgets[0].choices = choices

    def _get_choices(self):
        """
        The choices for this widget are the Select widget's choices
        """
        return self.widgets[0].choices
    choices = property(_get_choices, _set_choices)


class WidgetTests(TestCase):
    def test_12048(self):
        # See ticket #12048.
        w1 = SelectAndTextWidget(choices=[1, 2, 3])
        w2 = copy.deepcopy(w1)
        w2.choices = [4, 5, 6]
        # w2 ought to be independent of w1, since MultiWidget ought
        # to make a copy of its sub-widgets when it is copied.
        self.assertEqual(w1.choices, [1, 2, 3])

    @ignore_warnings(category=RemovedInDjango19Warning)
    def test_13390(self):
        # See ticket #13390
        class SplitDateForm(Form):
            field = DateTimeField(widget=SplitDateTimeWidget, required=False)

        form = SplitDateForm({'field': ''})
        self.assertTrue(form.is_valid())
        form = SplitDateForm({'field': ['', '']})
        self.assertTrue(form.is_valid())

        class SplitDateRequiredForm(Form):
            field = DateTimeField(widget=SplitDateTimeWidget, required=True)

        form = SplitDateRequiredForm({'field': ''})
        self.assertFalse(form.is_valid())
        form = SplitDateRequiredForm({'field': ['', '']})
        self.assertFalse(form.is_valid())


@override_settings(ROOT_URLCONF='forms_tests.urls')
class LiveWidgetTests(AdminSeleniumWebDriverTestCase):

    available_apps = ['forms_tests'] + AdminSeleniumWebDriverTestCase.available_apps

    def test_textarea_trailing_newlines(self):
        """
        Test that a roundtrip on a ModelForm doesn't alter the TextField value
        """
        article = Article.objects.create(content="\nTst\n")
        self.selenium.get('%s%s' % (self.live_server_url,
            reverse('article_form', args=[article.pk])))
        self.selenium.find_element_by_id('submit').submit()
        article = Article.objects.get(pk=article.pk)
        # Should be "\nTst\n" after #19251 is fixed
        self.assertEqual(article.content, "\r\nTst\r\n")


@python_2_unicode_compatible
class FakeFieldFile(object):
    """
    Quacks like a FieldFile (has a .url and unicode representation), but
    doesn't require us to care about storages etc.

    """
    url = 'something'

    def __str__(self):
        return self.url


class ClearableFileInputTests(TestCase):
    def test_clear_input_renders(self):
        """
        A ClearableFileInput with is_required False and rendered with
        an initial value that is a file renders a clear checkbox.

        """
        widget = ClearableFileInput()
        widget.is_required = False
        self.assertHTMLEqual(widget.render('myfile', FakeFieldFile()),
                         'Currently: <a href="something">something</a> <input type="checkbox" name="myfile-clear" id="myfile-clear_id" /> <label for="myfile-clear_id">Clear</label><br />Change: <input type="file" name="myfile" />')

    def test_html_escaped(self):
        """
        A ClearableFileInput should escape name, filename and URL when
        rendering HTML. Refs #15182.
        """

        @python_2_unicode_compatible
        class StrangeFieldFile(object):
            url = "something?chapter=1&sect=2&copy=3&lang=en"

            def __str__(self):
                return '''something<div onclick="alert('oops')">.jpg'''

        widget = ClearableFileInput()
        field = StrangeFieldFile()
        output = widget.render('my<div>file', field)
        self.assertNotIn(field.url, output)
        self.assertIn('href="something?chapter=1&amp;sect=2&amp;copy=3&amp;lang=en"', output)
        self.assertNotIn(six.text_type(field), output)
        self.assertIn('something&lt;div onclick=&quot;alert(&#39;oops&#39;)&quot;&gt;.jpg', output)
        self.assertIn('my&lt;div&gt;file', output)
        self.assertNotIn('my<div>file', output)

    def test_clear_input_renders_only_if_not_required(self):
        """
        A ClearableFileInput with is_required=False does not render a clear
        checkbox.

        """
        widget = ClearableFileInput()
        widget.is_required = True
        self.assertHTMLEqual(widget.render('myfile', FakeFieldFile()),
                         'Currently: <a href="something">something</a> <br />Change: <input type="file" name="myfile" />')

    def test_clear_input_renders_only_if_initial(self):
        """
        A ClearableFileInput instantiated with no initial value does not render
        a clear checkbox.

        """
        widget = ClearableFileInput()
        widget.is_required = False
        self.assertHTMLEqual(widget.render('myfile', None),
                         '<input type="file" name="myfile" />')

    def test_clear_input_checked_returns_false(self):
        """
        ClearableFileInput.value_from_datadict returns False if the clear
        checkbox is checked, if not required.

        """
        widget = ClearableFileInput()
        widget.is_required = False
        self.assertEqual(widget.value_from_datadict(
            data={'myfile-clear': True},
            files={},
            name='myfile'), False)

    def test_clear_input_checked_returns_false_only_if_not_required(self):
        """
        ClearableFileInput.value_from_datadict never returns False if the field
        is required.

        """
        widget = ClearableFileInput()
        widget.is_required = True
        f = SimpleUploadedFile('something.txt', b'content')
        self.assertEqual(widget.value_from_datadict(
            data={'myfile-clear': True},
            files={'myfile': f},
            name='myfile'), f)

    def test_render_custom_template(self):
        widget = ClearableFileInput()
        widget.template_with_initial = (
            '%(initial_text)s: <img src="%(initial_url)s" alt="%(initial)s" /> '
            '%(clear_template)s<br />%(input_text)s: %(input)s'
        )
        self.assertHTMLEqual(
            widget.render('myfile', FakeFieldFile()),
            'Currently: <img src="something" alt="something" /> '
            '<input type="checkbox" name="myfile-clear" id="myfile-clear_id" /> '
            '<label for="myfile-clear_id">Clear</label><br />Change: <input type="file" name="myfile" />'
        )
