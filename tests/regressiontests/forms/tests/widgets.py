# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal
import re
import time
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import *
from django.forms.widgets import RadioFieldRenderer
from django.utils import copycompat as copy
from django.utils import formats
from django.utils.safestring import mark_safe
from django.utils.translation import activate, deactivate
from django.utils.unittest import TestCase



class FormsWidgetTestCase(TestCase):
    # Each Widget class corresponds to an HTML form widget. A Widget knows how to
    # render itself, given a field name and some data. Widgets don't perform
    # validation.
    def test_textinput(self):
        w = TextInput()
        self.assertEqual(w.render('email', ''), u'<input type="text" name="email" />')
        self.assertEqual(w.render('email', None), u'<input type="text" name="email" />')
        self.assertEqual(w.render('email', 'test@example.com'), u'<input type="text" name="email" value="test@example.com" />')
        self.assertEqual(w.render('email', 'some "quoted" & ampersanded value'), u'<input type="text" name="email" value="some &quot;quoted&quot; &amp; ampersanded value" />')
        self.assertEqual(w.render('email', 'test@example.com', attrs={'class': 'fun'}), u'<input type="text" name="email" value="test@example.com" class="fun" />')

        # Note that doctest in Python 2.4 (and maybe 2.5?) doesn't support non-ascii
        # characters in output, so we're displaying the repr() here.
        self.assertEqual(w.render('email', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'}), u'<input type="text" name="email" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" class="fun" />')

        # You can also pass 'attrs' to the constructor:
        w = TextInput(attrs={'class': 'fun'})
        self.assertEqual(w.render('email', ''), u'<input type="text" class="fun" name="email" />')
        self.assertEqual(w.render('email', 'foo@example.com'), u'<input type="text" class="fun" value="foo@example.com" name="email" />')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = TextInput(attrs={'class': 'pretty'})
        self.assertEqual(w.render('email', '', attrs={'class': 'special'}), u'<input type="text" class="special" name="email" />')

        # 'attrs' can be safe-strings if needed)
        w = TextInput(attrs={'onBlur': mark_safe("function('foo')")})
        self.assertEqual(w.render('email', ''), u'<input onBlur="function(\'foo\')" type="text" name="email" />')

    def test_passwordinput(self):
        w = PasswordInput()
        self.assertEqual(w.render('email', ''), u'<input type="password" name="email" />')
        self.assertEqual(w.render('email', None), u'<input type="password" name="email" />')
        self.assertEqual(w.render('email', 'secret'), u'<input type="password" name="email" />')

        # The render_value argument lets you specify whether the widget should render
        # its value. For security reasons, this is off by default.
        w = PasswordInput(render_value=True)
        self.assertEqual(w.render('email', ''), u'<input type="password" name="email" />')
        self.assertEqual(w.render('email', None), u'<input type="password" name="email" />')
        self.assertEqual(w.render('email', 'test@example.com'), u'<input type="password" name="email" value="test@example.com" />')
        self.assertEqual(w.render('email', 'some "quoted" & ampersanded value'), u'<input type="password" name="email" value="some &quot;quoted&quot; &amp; ampersanded value" />')
        self.assertEqual(w.render('email', 'test@example.com', attrs={'class': 'fun'}), u'<input type="password" name="email" value="test@example.com" class="fun" />')

        # You can also pass 'attrs' to the constructor:
        w = PasswordInput(attrs={'class': 'fun'}, render_value=True)
        self.assertEqual(w.render('email', ''), u'<input type="password" class="fun" name="email" />')
        self.assertEqual(w.render('email', 'foo@example.com'), u'<input type="password" class="fun" value="foo@example.com" name="email" />')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = PasswordInput(attrs={'class': 'pretty'}, render_value=True)
        self.assertEqual(w.render('email', '', attrs={'class': 'special'}), u'<input type="password" class="special" name="email" />')

        self.assertEqual(w.render('email', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'}), u'<input type="password" class="fun" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" name="email" />')

    def test_hiddeninput(self):
        w = HiddenInput()
        self.assertEqual(w.render('email', ''), u'<input type="hidden" name="email" />')
        self.assertEqual(w.render('email', None), u'<input type="hidden" name="email" />')
        self.assertEqual(w.render('email', 'test@example.com'), u'<input type="hidden" name="email" value="test@example.com" />')
        self.assertEqual(w.render('email', 'some "quoted" & ampersanded value'), u'<input type="hidden" name="email" value="some &quot;quoted&quot; &amp; ampersanded value" />')
        self.assertEqual(w.render('email', 'test@example.com', attrs={'class': 'fun'}), u'<input type="hidden" name="email" value="test@example.com" class="fun" />')

        # You can also pass 'attrs' to the constructor:
        w = HiddenInput(attrs={'class': 'fun'})
        self.assertEqual(w.render('email', ''), u'<input type="hidden" class="fun" name="email" />')
        self.assertEqual(w.render('email', 'foo@example.com'), u'<input type="hidden" class="fun" value="foo@example.com" name="email" />')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = HiddenInput(attrs={'class': 'pretty'})
        self.assertEqual(w.render('email', '', attrs={'class': 'special'}), u'<input type="hidden" class="special" name="email" />')

        self.assertEqual(w.render('email', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'}), u'<input type="hidden" class="fun" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" name="email" />')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = HiddenInput(attrs={'class': 'pretty'})
        self.assertEqual(w.render('email', '', attrs={'class': 'special'}), u'<input type="hidden" class="special" name="email" />')

        # Boolean values are rendered to their string forms ("True" and "False").
        w = HiddenInput()
        self.assertEqual(w.render('get_spam', False), u'<input type="hidden" name="get_spam" value="False" />')
        self.assertEqual(w.render('get_spam', True), u'<input type="hidden" name="get_spam" value="True" />')

    def test_multiplehiddeninput(self):
        w = MultipleHiddenInput()
        self.assertEqual(w.render('email', []), u'')
        self.assertEqual(w.render('email', None), u'')
        self.assertEqual(w.render('email', ['test@example.com']), u'<input type="hidden" name="email" value="test@example.com" />')
        self.assertEqual(w.render('email', ['some "quoted" & ampersanded value']), u'<input type="hidden" name="email" value="some &quot;quoted&quot; &amp; ampersanded value" />')
        self.assertEqual(w.render('email', ['test@example.com', 'foo@example.com']), u'<input type="hidden" name="email" value="test@example.com" />\n<input type="hidden" name="email" value="foo@example.com" />')
        self.assertEqual(w.render('email', ['test@example.com'], attrs={'class': 'fun'}), u'<input type="hidden" name="email" value="test@example.com" class="fun" />')
        self.assertEqual(w.render('email', ['test@example.com', 'foo@example.com'], attrs={'class': 'fun'}), u'<input type="hidden" name="email" value="test@example.com" class="fun" />\n<input type="hidden" name="email" value="foo@example.com" class="fun" />')

        # You can also pass 'attrs' to the constructor:
        w = MultipleHiddenInput(attrs={'class': 'fun'})
        self.assertEqual(w.render('email', []), u'')
        self.assertEqual(w.render('email', ['foo@example.com']), u'<input type="hidden" class="fun" value="foo@example.com" name="email" />')
        self.assertEqual(w.render('email', ['foo@example.com', 'test@example.com']), u'<input type="hidden" class="fun" value="foo@example.com" name="email" />\n<input type="hidden" class="fun" value="test@example.com" name="email" />')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = MultipleHiddenInput(attrs={'class': 'pretty'})
        self.assertEqual(w.render('email', ['foo@example.com'], attrs={'class': 'special'}), u'<input type="hidden" class="special" value="foo@example.com" name="email" />')

        self.assertEqual(w.render('email', ['ŠĐĆŽćžšđ'], attrs={'class': 'fun'}), u'<input type="hidden" class="fun" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" name="email" />')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = MultipleHiddenInput(attrs={'class': 'pretty'})
        self.assertEqual(w.render('email', ['foo@example.com'], attrs={'class': 'special'}), u'<input type="hidden" class="special" value="foo@example.com" name="email" />')

        # Each input gets a separate ID.
        w = MultipleHiddenInput()
        self.assertEqual(w.render('letters', list('abc'), attrs={'id': 'hideme'}), u'<input type="hidden" name="letters" value="a" id="hideme_0" />\n<input type="hidden" name="letters" value="b" id="hideme_1" />\n<input type="hidden" name="letters" value="c" id="hideme_2" />')

    def test_fileinput(self):
        # FileInput widgets don't ever show the value, because the old value is of no use
        # if you are updating the form or if the provided file generated an error.
        w = FileInput()
        self.assertEqual(w.render('email', ''), u'<input type="file" name="email" />')
        self.assertEqual(w.render('email', None), u'<input type="file" name="email" />')
        self.assertEqual(w.render('email', 'test@example.com'), u'<input type="file" name="email" />')
        self.assertEqual(w.render('email', 'some "quoted" & ampersanded value'), u'<input type="file" name="email" />')
        self.assertEqual(w.render('email', 'test@example.com', attrs={'class': 'fun'}), u'<input type="file" name="email" class="fun" />')

        # You can also pass 'attrs' to the constructor:
        w = FileInput(attrs={'class': 'fun'})
        self.assertEqual(w.render('email', ''), u'<input type="file" class="fun" name="email" />')
        self.assertEqual(w.render('email', 'foo@example.com'), u'<input type="file" class="fun" name="email" />')

        self.assertEqual(w.render('email', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'}), u'<input type="file" class="fun" name="email" />')

        # Test for the behavior of _has_changed for FileInput. The value of data will
        # more than likely come from request.FILES. The value of initial data will
        # likely be a filename stored in the database. Since its value is of no use to
        # a FileInput it is ignored.
        w = FileInput()

        # No file was uploaded and no initial data.
        self.assertFalse(w._has_changed(u'', None))

        # A file was uploaded and no initial data.
        self.assertTrue(w._has_changed(u'', {'filename': 'resume.txt', 'content': 'My resume'}))

        # A file was not uploaded, but there is initial data
        self.assertFalse(w._has_changed(u'resume.txt', None))

        # A file was uploaded and there is initial data (file identity is not dealt
        # with here)
        self.assertTrue(w._has_changed('resume.txt', {'filename': 'resume.txt', 'content': 'My resume'}))

    def test_textarea(self):
        w = Textarea()
        self.assertEqual(w.render('msg', ''), u'<textarea rows="10" cols="40" name="msg"></textarea>')
        self.assertEqual(w.render('msg', None), u'<textarea rows="10" cols="40" name="msg"></textarea>')
        self.assertEqual(w.render('msg', 'value'), u'<textarea rows="10" cols="40" name="msg">value</textarea>')
        self.assertEqual(w.render('msg', 'some "quoted" & ampersanded value'), u'<textarea rows="10" cols="40" name="msg">some &quot;quoted&quot; &amp; ampersanded value</textarea>')
        self.assertEqual(w.render('msg', mark_safe('pre &quot;quoted&quot; value')), u'<textarea rows="10" cols="40" name="msg">pre &quot;quoted&quot; value</textarea>')
        self.assertEqual(w.render('msg', 'value', attrs={'class': 'pretty', 'rows': 20}), u'<textarea class="pretty" rows="20" cols="40" name="msg">value</textarea>')

        # You can also pass 'attrs' to the constructor:
        w = Textarea(attrs={'class': 'pretty'})
        self.assertEqual(w.render('msg', ''), u'<textarea rows="10" cols="40" name="msg" class="pretty"></textarea>')
        self.assertEqual(w.render('msg', 'example'), u'<textarea rows="10" cols="40" name="msg" class="pretty">example</textarea>')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = Textarea(attrs={'class': 'pretty'})
        self.assertEqual(w.render('msg', '', attrs={'class': 'special'}), u'<textarea rows="10" cols="40" name="msg" class="special"></textarea>')

        self.assertEqual(w.render('msg', 'ŠĐĆŽćžšđ', attrs={'class': 'fun'}), u'<textarea rows="10" cols="40" name="msg" class="fun">\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111</textarea>')

    def test_checkboxinput(self):
        w = CheckboxInput()
        self.assertEqual(w.render('is_cool', ''), u'<input type="checkbox" name="is_cool" />')
        self.assertEqual(w.render('is_cool', None), u'<input type="checkbox" name="is_cool" />')
        self.assertEqual(w.render('is_cool', False), u'<input type="checkbox" name="is_cool" />')
        self.assertEqual(w.render('is_cool', True), u'<input checked="checked" type="checkbox" name="is_cool" />')

        # Using any value that's not in ('', None, False, True) will check the checkbox
        # and set the 'value' attribute.
        self.assertEqual(w.render('is_cool', 'foo'), u'<input checked="checked" type="checkbox" name="is_cool" value="foo" />')

        self.assertEqual(w.render('is_cool', False, attrs={'class': 'pretty'}), u'<input type="checkbox" name="is_cool" class="pretty" />')

        # You can also pass 'attrs' to the constructor:
        w = CheckboxInput(attrs={'class': 'pretty'})
        self.assertEqual(w.render('is_cool', ''), u'<input type="checkbox" class="pretty" name="is_cool" />')

        # 'attrs' passed to render() get precedence over those passed to the constructor:
        w = CheckboxInput(attrs={'class': 'pretty'})
        self.assertEqual(w.render('is_cool', '', attrs={'class': 'special'}), u'<input type="checkbox" class="special" name="is_cool" />')

        # You can pass 'check_test' to the constructor. This is a callable that takes the
        # value and returns True if the box should be checked.
        w = CheckboxInput(check_test=lambda value: value.startswith('hello'))
        self.assertEqual(w.render('greeting', ''), u'<input type="checkbox" name="greeting" />')
        self.assertEqual(w.render('greeting', 'hello'), u'<input checked="checked" type="checkbox" name="greeting" value="hello" />')
        self.assertEqual(w.render('greeting', 'hello there'), u'<input checked="checked" type="checkbox" name="greeting" value="hello there" />')
        self.assertEqual(w.render('greeting', 'hello & goodbye'), u'<input checked="checked" type="checkbox" name="greeting" value="hello &amp; goodbye" />')

        # A subtlety: If the 'check_test' argument cannot handle a value and raises any
        # exception during its __call__, then the exception will be swallowed and the box
        # will not be checked. In this example, the 'check_test' assumes the value has a
        # startswith() method, which fails for the values True, False and None.
        self.assertEqual(w.render('greeting', True), u'<input type="checkbox" name="greeting" />')
        self.assertEqual(w.render('greeting', False), u'<input type="checkbox" name="greeting" />')
        self.assertEqual(w.render('greeting', None), u'<input type="checkbox" name="greeting" />')

        # The CheckboxInput widget will return False if the key is not found in the data
        # dictionary (because HTML form submission doesn't send any result for unchecked
        # checkboxes).
        self.assertFalse(w.value_from_datadict({}, {}, 'testing'))

        self.assertFalse(w._has_changed(None, None))
        self.assertFalse(w._has_changed(None, u''))
        self.assertFalse(w._has_changed(u'', None))
        self.assertFalse(w._has_changed(u'', u''))
        self.assertTrue(w._has_changed(False, u'on'))
        self.assertFalse(w._has_changed(True, u'on'))
        self.assertTrue(w._has_changed(True, u''))

    def test_select(self):
        w = Select()
        self.assertEqual(w.render('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select name="beatle">
<option value="J" selected="selected">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>""")

        # If the value is None, none of the options are selected:
        self.assertEqual(w.render('beatle', None, choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select name="beatle">
<option value="J">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>""")

        # If the value corresponds to a label (but not to an option value), none of the options are selected:
        self.assertEqual(w.render('beatle', 'John', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select name="beatle">
<option value="J">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>""")

        # The value is compared to its str():
        self.assertEqual(w.render('num', 2, choices=[('1', '1'), ('2', '2'), ('3', '3')]), """<select name="num">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")
        self.assertEqual(w.render('num', '2', choices=[(1, 1), (2, 2), (3, 3)]), """<select name="num">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")
        self.assertEqual(w.render('num', 2, choices=[(1, 1), (2, 2), (3, 3)]), """<select name="num">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")

        # The 'choices' argument can be any iterable:
        from itertools import chain
        def get_choices():
            for i in range(5):
                yield (i, i)
        self.assertEqual(w.render('num', 2, choices=get_choices()), """<select name="num">
<option value="0">0</option>
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
<option value="4">4</option>
</select>""")
        things = ({'id': 1, 'name': 'And Boom'}, {'id': 2, 'name': 'One More Thing!'})
        class SomeForm(Form):
            somechoice = ChoiceField(choices=chain((('', '-'*9),), [(thing['id'], thing['name']) for thing in things]))
        f = SomeForm()
        self.assertEqual(f.as_table(), u'<tr><th><label for="id_somechoice">Somechoice:</label></th><td><select name="somechoice" id="id_somechoice">\n<option value="" selected="selected">---------</option>\n<option value="1">And Boom</option>\n<option value="2">One More Thing!</option>\n</select></td></tr>')
        self.assertEqual(f.as_table(), u'<tr><th><label for="id_somechoice">Somechoice:</label></th><td><select name="somechoice" id="id_somechoice">\n<option value="" selected="selected">---------</option>\n<option value="1">And Boom</option>\n<option value="2">One More Thing!</option>\n</select></td></tr>')
        f = SomeForm({'somechoice': 2})
        self.assertEqual(f.as_table(), u'<tr><th><label for="id_somechoice">Somechoice:</label></th><td><select name="somechoice" id="id_somechoice">\n<option value="">---------</option>\n<option value="1">And Boom</option>\n<option value="2" selected="selected">One More Thing!</option>\n</select></td></tr>')

        # You can also pass 'choices' to the constructor:
        w = Select(choices=[(1, 1), (2, 2), (3, 3)])
        self.assertEqual(w.render('num', 2), """<select name="num">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")

        # If 'choices' is passed to both the constructor and render(), then they'll both be in the output:
        self.assertEqual(w.render('num', 2, choices=[(4, 4), (5, 5)]), """<select name="num">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
<option value="4">4</option>
<option value="5">5</option>
</select>""")

        # Choices are escaped correctly
        self.assertEqual(w.render('escape', None, choices=(('bad', 'you & me'), ('good', mark_safe('you &gt; me')))), """<select name="escape">
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="bad">you &amp; me</option>
<option value="good">you &gt; me</option>
</select>""")

        # Unicode choices are correctly rendered as HTML
        self.assertEqual(w.render('email', 'ŠĐĆŽćžšđ', choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')]), u'<select name="email">\n<option value="1">1</option>\n<option value="2">2</option>\n<option value="3">3</option>\n<option value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" selected="selected">\u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111</option>\n<option value="\u0107\u017e\u0161\u0111">abc\u0107\u017e\u0161\u0111</option>\n</select>')

        # If choices is passed to the constructor and is a generator, it can be iterated
        # over multiple times without getting consumed:
        w = Select(choices=get_choices())
        self.assertEqual(w.render('num', 2), """<select name="num">
<option value="0">0</option>
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
<option value="4">4</option>
</select>""")
        self.assertEqual(w.render('num', 3), """<select name="num">
<option value="0">0</option>
<option value="1">1</option>
<option value="2">2</option>
<option value="3" selected="selected">3</option>
<option value="4">4</option>
</select>""")

        # Choices can be nested one level in order to create HTML optgroups:
        w.choices=(('outer1', 'Outer 1'), ('Group "1"', (('inner1', 'Inner 1'), ('inner2', 'Inner 2'))))
        self.assertEqual(w.render('nestchoice', None), """<select name="nestchoice">
<option value="outer1">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>""")

        self.assertEqual(w.render('nestchoice', 'outer1'), """<select name="nestchoice">
<option value="outer1" selected="selected">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>""")

        self.assertEqual(w.render('nestchoice', 'inner1'), """<select name="nestchoice">
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
        self.assertEqual(w.render('is_cool', False), """<select name="is_cool">
<option value="1">Unknown</option>
<option value="2">Yes</option>
<option value="3" selected="selected">No</option>
</select>""")
        self.assertEqual(w.render('is_cool', None), """<select name="is_cool">
<option value="1" selected="selected">Unknown</option>
<option value="2">Yes</option>
<option value="3">No</option>
</select>""")
        self.assertEqual(w.render('is_cool', '2'), """<select name="is_cool">
<option value="1">Unknown</option>
<option value="2" selected="selected">Yes</option>
<option value="3">No</option>
</select>""")
        self.assertEqual(w.render('is_cool', '3'), """<select name="is_cool">
<option value="1">Unknown</option>
<option value="2">Yes</option>
<option value="3" selected="selected">No</option>
</select>""")
        self.assertTrue(w._has_changed(False, None))
        self.assertTrue(w._has_changed(None, False))
        self.assertFalse(w._has_changed(None, None))
        self.assertFalse(w._has_changed(False, False))
        self.assertTrue(w._has_changed(True, False))
        self.assertTrue(w._has_changed(True, None))
        self.assertTrue(w._has_changed(True, False))

    def test_selectmultiple(self):
        w = SelectMultiple()
        self.assertEqual(w.render('beatles', ['J'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select multiple="multiple" name="beatles">
<option value="J" selected="selected">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>""")
        self.assertEqual(w.render('beatles', ['J', 'P'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select multiple="multiple" name="beatles">
<option value="J" selected="selected">John</option>
<option value="P" selected="selected">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>""")
        self.assertEqual(w.render('beatles', ['J', 'P', 'R'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select multiple="multiple" name="beatles">
<option value="J" selected="selected">John</option>
<option value="P" selected="selected">Paul</option>
<option value="G">George</option>
<option value="R" selected="selected">Ringo</option>
</select>""")

        # If the value is None, none of the options are selected:
        self.assertEqual(w.render('beatles', None, choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select multiple="multiple" name="beatles">
<option value="J">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>""")

        # If the value corresponds to a label (but not to an option value), none of the options are selected:
        self.assertEqual(w.render('beatles', ['John'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select multiple="multiple" name="beatles">
<option value="J">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>""")

        # If multiple values are given, but some of them are not valid, the valid ones are selected:
        self.assertEqual(w.render('beatles', ['J', 'G', 'foo'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<select multiple="multiple" name="beatles">
<option value="J" selected="selected">John</option>
<option value="P">Paul</option>
<option value="G" selected="selected">George</option>
<option value="R">Ringo</option>
</select>""")

        # The value is compared to its str():
        self.assertEqual(w.render('nums', [2], choices=[('1', '1'), ('2', '2'), ('3', '3')]), """<select multiple="multiple" name="nums">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")
        self.assertEqual(w.render('nums', ['2'], choices=[(1, 1), (2, 2), (3, 3)]), """<select multiple="multiple" name="nums">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")
        self.assertEqual(w.render('nums', [2], choices=[(1, 1), (2, 2), (3, 3)]), """<select multiple="multiple" name="nums">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")

        # The 'choices' argument can be any iterable:
        def get_choices():
            for i in range(5):
                yield (i, i)
        self.assertEqual(w.render('nums', [2], choices=get_choices()), """<select multiple="multiple" name="nums">
<option value="0">0</option>
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
<option value="4">4</option>
</select>""")

        # You can also pass 'choices' to the constructor:
        w = SelectMultiple(choices=[(1, 1), (2, 2), (3, 3)])
        self.assertEqual(w.render('nums', [2]), """<select multiple="multiple" name="nums">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
</select>""")

        # If 'choices' is passed to both the constructor and render(), then they'll both be in the output:
        self.assertEqual(w.render('nums', [2], choices=[(4, 4), (5, 5)]), """<select multiple="multiple" name="nums">
<option value="1">1</option>
<option value="2" selected="selected">2</option>
<option value="3">3</option>
<option value="4">4</option>
<option value="5">5</option>
</select>""")

        # Choices are escaped correctly
        self.assertEqual(w.render('escape', None, choices=(('bad', 'you & me'), ('good', mark_safe('you &gt; me')))), """<select multiple="multiple" name="escape">
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="bad">you &amp; me</option>
<option value="good">you &gt; me</option>
</select>""")

        # Unicode choices are correctly rendered as HTML
        self.assertEqual(w.render('nums', ['ŠĐĆŽćžšđ'], choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')]), u'<select multiple="multiple" name="nums">\n<option value="1">1</option>\n<option value="2">2</option>\n<option value="3">3</option>\n<option value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" selected="selected">\u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111</option>\n<option value="\u0107\u017e\u0161\u0111">abc\u0107\u017e\u0161\u0111</option>\n</select>')

        # Test the usage of _has_changed
        self.assertFalse(w._has_changed(None, None))
        self.assertFalse(w._has_changed([], None))
        self.assertTrue(w._has_changed(None, [u'1']))
        self.assertFalse(w._has_changed([1, 2], [u'1', u'2']))
        self.assertTrue(w._has_changed([1, 2], [u'1']))
        self.assertTrue(w._has_changed([1, 2], [u'1', u'3']))

        # Choices can be nested one level in order to create HTML optgroups:
        w.choices = (('outer1', 'Outer 1'), ('Group "1"', (('inner1', 'Inner 1'), ('inner2', 'Inner 2'))))
        self.assertEqual(w.render('nestchoice', None), """<select multiple="multiple" name="nestchoice">
<option value="outer1">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>""")

        self.assertEqual(w.render('nestchoice', ['outer1']), """<select multiple="multiple" name="nestchoice">
<option value="outer1" selected="selected">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>""")

        self.assertEqual(w.render('nestchoice', ['inner1']), """<select multiple="multiple" name="nestchoice">
<option value="outer1">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1" selected="selected">Inner 1</option>
<option value="inner2">Inner 2</option>
</optgroup>
</select>""")

        self.assertEqual(w.render('nestchoice', ['outer1', 'inner2']), """<select multiple="multiple" name="nestchoice">
<option value="outer1" selected="selected">Outer 1</option>
<optgroup label="Group &quot;1&quot;">
<option value="inner1">Inner 1</option>
<option value="inner2" selected="selected">Inner 2</option>
</optgroup>
</select>""")

    def test_radioselect(self):
        w = RadioSelect()
        self.assertEqual(w.render('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input checked="checked" type="radio" name="beatle" value="J" /> John</label></li>
<li><label><input type="radio" name="beatle" value="P" /> Paul</label></li>
<li><label><input type="radio" name="beatle" value="G" /> George</label></li>
<li><label><input type="radio" name="beatle" value="R" /> Ringo</label></li>
</ul>""")

        # If the value is None, none of the options are checked:
        self.assertEqual(w.render('beatle', None, choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input type="radio" name="beatle" value="J" /> John</label></li>
<li><label><input type="radio" name="beatle" value="P" /> Paul</label></li>
<li><label><input type="radio" name="beatle" value="G" /> George</label></li>
<li><label><input type="radio" name="beatle" value="R" /> Ringo</label></li>
</ul>""")

        # If the value corresponds to a label (but not to an option value), none of the options are checked:
        self.assertEqual(w.render('beatle', 'John', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input type="radio" name="beatle" value="J" /> John</label></li>
<li><label><input type="radio" name="beatle" value="P" /> Paul</label></li>
<li><label><input type="radio" name="beatle" value="G" /> George</label></li>
<li><label><input type="radio" name="beatle" value="R" /> Ringo</label></li>
</ul>""")

        # The value is compared to its str():
        self.assertEqual(w.render('num', 2, choices=[('1', '1'), ('2', '2'), ('3', '3')]), """<ul>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
</ul>""")
        self.assertEqual(w.render('num', '2', choices=[(1, 1), (2, 2), (3, 3)]), """<ul>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
</ul>""")
        self.assertEqual(w.render('num', 2, choices=[(1, 1), (2, 2), (3, 3)]), """<ul>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
</ul>""")

        # The 'choices' argument can be any iterable:
        def get_choices():
            for i in range(5):
                yield (i, i)
        self.assertEqual(w.render('num', 2, choices=get_choices()), """<ul>
<li><label><input type="radio" name="num" value="0" /> 0</label></li>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
<li><label><input type="radio" name="num" value="4" /> 4</label></li>
</ul>""")

        # You can also pass 'choices' to the constructor:
        w = RadioSelect(choices=[(1, 1), (2, 2), (3, 3)])
        self.assertEqual(w.render('num', 2), """<ul>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
</ul>""")

        # If 'choices' is passed to both the constructor and render(), then they'll both be in the output:
        self.assertEqual(w.render('num', 2, choices=[(4, 4), (5, 5)]), """<ul>
<li><label><input type="radio" name="num" value="1" /> 1</label></li>
<li><label><input checked="checked" type="radio" name="num" value="2" /> 2</label></li>
<li><label><input type="radio" name="num" value="3" /> 3</label></li>
<li><label><input type="radio" name="num" value="4" /> 4</label></li>
<li><label><input type="radio" name="num" value="5" /> 5</label></li>
</ul>""")

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

        self.assertEqual('\n'.join(inp_set1), """<label><input checked="checked" type="radio" name="beatle" value="J" /> John</label>
<label><input type="radio" name="beatle" value="P" /> Paul</label>
<label><input type="radio" name="beatle" value="G" /> George</label>
<label><input type="radio" name="beatle" value="R" /> Ringo</label>""")
        self.assertEqual('\n'.join(inp_set2), """<label><input checked="checked" type="radio" name="beatle" value="J" /> John</label><br />
<label><input type="radio" name="beatle" value="P" /> Paul</label><br />
<label><input type="radio" name="beatle" value="G" /> George</label><br />
<label><input type="radio" name="beatle" value="R" /> Ringo</label><br />""")
        self.assertEqual('\n'.join(inp_set3), """<p><input checked="checked" type="radio" name="beatle" value="J" /> John</p>
<p><input type="radio" name="beatle" value="P" /> Paul</p>
<p><input type="radio" name="beatle" value="G" /> George</p>
<p><input type="radio" name="beatle" value="R" /> Ringo</p>""")
        self.assertEqual('\n'.join(inp_set4), """beatle J J John True
beatle J P Paul False
beatle J G George False
beatle J R Ringo False""")

        # You can create your own custom renderers for RadioSelect to use.
        class MyRenderer(RadioFieldRenderer):
           def render(self):
               return u'<br />\n'.join([unicode(choice) for choice in self])
        w = RadioSelect(renderer=MyRenderer)
        self.assertEqual(w.render('beatle', 'G', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<label><input type="radio" name="beatle" value="J" /> John</label><br />
<label><input type="radio" name="beatle" value="P" /> Paul</label><br />
<label><input checked="checked" type="radio" name="beatle" value="G" /> George</label><br />
<label><input type="radio" name="beatle" value="R" /> Ringo</label>""")

        # Or you can use custom RadioSelect fields that use your custom renderer.
        class CustomRadioSelect(RadioSelect):
           renderer = MyRenderer
        w = CustomRadioSelect()
        self.assertEqual(w.render('beatle', 'G', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<label><input type="radio" name="beatle" value="J" /> John</label><br />
<label><input type="radio" name="beatle" value="P" /> Paul</label><br />
<label><input checked="checked" type="radio" name="beatle" value="G" /> George</label><br />
<label><input type="radio" name="beatle" value="R" /> Ringo</label>""")

        # A RadioFieldRenderer object also allows index access to individual RadioInput
        w = RadioSelect()
        r = w.get_renderer('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')))
        self.assertEqual(str(r[1]), '<label><input type="radio" name="beatle" value="P" /> Paul</label>')
        self.assertEqual(str(r[0]), '<label><input checked="checked" type="radio" name="beatle" value="J" /> John</label>')
        self.assertTrue(r[0].is_checked())
        self.assertFalse(r[1].is_checked())
        self.assertEqual((r[1].name, r[1].value, r[1].choice_value, r[1].choice_label), ('beatle', u'J', u'P', u'Paul'))

        try:
            r[10]
            self.fail("This offset should not exist.")
        except IndexError:
            pass

        # Choices are escaped correctly
        w = RadioSelect()
        self.assertEqual(w.render('escape', None, choices=(('bad', 'you & me'), ('good', mark_safe('you &gt; me')))), """<ul>
<li><label><input type="radio" name="escape" value="bad" /> you &amp; me</label></li>
<li><label><input type="radio" name="escape" value="good" /> you &gt; me</label></li>
</ul>""")

        # Unicode choices are correctly rendered as HTML
        w = RadioSelect()
        self.assertEqual(unicode(w.render('email', 'ŠĐĆŽćžšđ', choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')])), u'<ul>\n<li><label><input checked="checked" type="radio" name="email" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" /> \u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111</label></li>\n<li><label><input type="radio" name="email" value="\u0107\u017e\u0161\u0111" /> abc\u0107\u017e\u0161\u0111</label></li>\n</ul>')

        # Attributes provided at instantiation are passed to the constituent inputs
        w = RadioSelect(attrs={'id':'foo'})
        self.assertEqual(w.render('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label for="foo_0"><input checked="checked" type="radio" id="foo_0" value="J" name="beatle" /> John</label></li>
<li><label for="foo_1"><input type="radio" id="foo_1" value="P" name="beatle" /> Paul</label></li>
<li><label for="foo_2"><input type="radio" id="foo_2" value="G" name="beatle" /> George</label></li>
<li><label for="foo_3"><input type="radio" id="foo_3" value="R" name="beatle" /> Ringo</label></li>
</ul>""")

        # Attributes provided at render-time are passed to the constituent inputs
        w = RadioSelect()
        self.assertEqual(w.render('beatle', 'J', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')), attrs={'id':'bar'}), """<ul>
<li><label for="bar_0"><input checked="checked" type="radio" id="bar_0" value="J" name="beatle" /> John</label></li>
<li><label for="bar_1"><input type="radio" id="bar_1" value="P" name="beatle" /> Paul</label></li>
<li><label for="bar_2"><input type="radio" id="bar_2" value="G" name="beatle" /> George</label></li>
<li><label for="bar_3"><input type="radio" id="bar_3" value="R" name="beatle" /> Ringo</label></li>
</ul>""")

    def test_checkboxselectmultiple(self):
        w = CheckboxSelectMultiple()
        self.assertEqual(w.render('beatles', ['J'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input checked="checked" type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>""")
        self.assertEqual(w.render('beatles', ['J', 'P'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input checked="checked" type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input checked="checked" type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>""")
        self.assertEqual(w.render('beatles', ['J', 'P', 'R'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input checked="checked" type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input checked="checked" type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input checked="checked" type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>""")

        # If the value is None, none of the options are selected:
        self.assertEqual(w.render('beatles', None, choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>""")

        # If the value corresponds to a label (but not to an option value), none of the options are selected:
        self.assertEqual(w.render('beatles', ['John'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>""")

        # If multiple values are given, but some of them are not valid, the valid ones are selected:
        self.assertEqual(w.render('beatles', ['J', 'G', 'foo'], choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))), """<ul>
<li><label><input checked="checked" type="checkbox" name="beatles" value="J" /> John</label></li>
<li><label><input type="checkbox" name="beatles" value="P" /> Paul</label></li>
<li><label><input checked="checked" type="checkbox" name="beatles" value="G" /> George</label></li>
<li><label><input type="checkbox" name="beatles" value="R" /> Ringo</label></li>
</ul>""")

        # The value is compared to its str():
        self.assertEqual(w.render('nums', [2], choices=[('1', '1'), ('2', '2'), ('3', '3')]), """<ul>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
</ul>""")
        self.assertEqual(w.render('nums', ['2'], choices=[(1, 1), (2, 2), (3, 3)]), """<ul>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
</ul>""")
        self.assertEqual(w.render('nums', [2], choices=[(1, 1), (2, 2), (3, 3)]), """<ul>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
</ul>""")

        # The 'choices' argument can be any iterable:
        def get_choices():
            for i in range(5):
                yield (i, i)
        self.assertEqual(w.render('nums', [2], choices=get_choices()), """<ul>
<li><label><input type="checkbox" name="nums" value="0" /> 0</label></li>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
<li><label><input type="checkbox" name="nums" value="4" /> 4</label></li>
</ul>""")

        # You can also pass 'choices' to the constructor:
        w = CheckboxSelectMultiple(choices=[(1, 1), (2, 2), (3, 3)])
        self.assertEqual(w.render('nums', [2]), """<ul>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
</ul>""")

        # If 'choices' is passed to both the constructor and render(), then they'll both be in the output:
        self.assertEqual(w.render('nums', [2], choices=[(4, 4), (5, 5)]), """<ul>
<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>
<li><label><input checked="checked" type="checkbox" name="nums" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>
<li><label><input type="checkbox" name="nums" value="4" /> 4</label></li>
<li><label><input type="checkbox" name="nums" value="5" /> 5</label></li>
</ul>""")

        # Choices are escaped correctly
        self.assertEqual(w.render('escape', None, choices=(('bad', 'you & me'), ('good', mark_safe('you &gt; me')))), """<ul>
<li><label><input type="checkbox" name="escape" value="1" /> 1</label></li>
<li><label><input type="checkbox" name="escape" value="2" /> 2</label></li>
<li><label><input type="checkbox" name="escape" value="3" /> 3</label></li>
<li><label><input type="checkbox" name="escape" value="bad" /> you &amp; me</label></li>
<li><label><input type="checkbox" name="escape" value="good" /> you &gt; me</label></li>
</ul>""")

        # Test the usage of _has_changed
        self.assertFalse(w._has_changed(None, None))
        self.assertFalse(w._has_changed([], None))
        self.assertTrue(w._has_changed(None, [u'1']))
        self.assertFalse(w._has_changed([1, 2], [u'1', u'2']))
        self.assertTrue(w._has_changed([1, 2], [u'1']))
        self.assertTrue(w._has_changed([1, 2], [u'1', u'3']))

        # Unicode choices are correctly rendered as HTML
        self.assertEqual(w.render('nums', ['ŠĐĆŽćžšđ'], choices=[('ŠĐĆŽćžšđ', 'ŠĐabcĆŽćžšđ'), ('ćžšđ', 'abcćžšđ')]), u'<ul>\n<li><label><input type="checkbox" name="nums" value="1" /> 1</label></li>\n<li><label><input type="checkbox" name="nums" value="2" /> 2</label></li>\n<li><label><input type="checkbox" name="nums" value="3" /> 3</label></li>\n<li><label><input checked="checked" type="checkbox" name="nums" value="\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111" /> \u0160\u0110abc\u0106\u017d\u0107\u017e\u0161\u0111</label></li>\n<li><label><input type="checkbox" name="nums" value="\u0107\u017e\u0161\u0111" /> abc\u0107\u017e\u0161\u0111</label></li>\n</ul>')

        # Each input gets a separate ID
        self.assertEqual(CheckboxSelectMultiple().render('letters', list('ac'), choices=zip(list('abc'), list('ABC')), attrs={'id': 'abc'}), """<ul>
<li><label for="abc_0"><input checked="checked" type="checkbox" name="letters" value="a" id="abc_0" /> A</label></li>
<li><label for="abc_1"><input type="checkbox" name="letters" value="b" id="abc_1" /> B</label></li>
<li><label for="abc_2"><input checked="checked" type="checkbox" name="letters" value="c" id="abc_2" /> C</label></li>
</ul>""")

    def test_multi(self):
        class MyMultiWidget(MultiWidget):
            def decompress(self, value):
                if value:
                    return value.split('__')
                return ['', '']
            def format_output(self, rendered_widgets):
                return u'<br />'.join(rendered_widgets)

        w = MyMultiWidget(widgets=(TextInput(attrs={'class': 'big'}), TextInput(attrs={'class': 'small'})))
        self.assertEqual(w.render('name', ['john', 'lennon']), u'<input type="text" class="big" value="john" name="name_0" /><br /><input type="text" class="small" value="lennon" name="name_1" />')
        self.assertEqual(w.render('name', 'john__lennon'), u'<input type="text" class="big" value="john" name="name_0" /><br /><input type="text" class="small" value="lennon" name="name_1" />')
        self.assertEqual(w.render('name', 'john__lennon', attrs={'id':'foo'}), u'<input id="foo_0" type="text" class="big" value="john" name="name_0" /><br /><input id="foo_1" type="text" class="small" value="lennon" name="name_1" />')
        w = MyMultiWidget(widgets=(TextInput(attrs={'class': 'big'}), TextInput(attrs={'class': 'small'})), attrs={'id': 'bar'})
        self.assertEqual(w.render('name', ['john', 'lennon']), u'<input id="bar_0" type="text" class="big" value="john" name="name_0" /><br /><input id="bar_1" type="text" class="small" value="lennon" name="name_1" />')

        w = MyMultiWidget(widgets=(TextInput(), TextInput()))

        # test with no initial data
        self.assertTrue(w._has_changed(None, [u'john', u'lennon']))

        # test when the data is the same as initial
        self.assertFalse(w._has_changed(u'john__lennon', [u'john', u'lennon']))

        # test when the first widget's data has changed
        self.assertTrue(w._has_changed(u'john__lennon', [u'alfred', u'lennon']))

        # test when the last widget's data has changed. this ensures that it is not
        # short circuiting while testing the widgets.
        self.assertTrue(w._has_changed(u'john__lennon', [u'john', u'denver']))

    def test_splitdatetime(self):
        w = SplitDateTimeWidget()
        self.assertEqual(w.render('date', ''), u'<input type="text" name="date_0" /><input type="text" name="date_1" />')
        self.assertEqual(w.render('date', None), u'<input type="text" name="date_0" /><input type="text" name="date_1" />')
        self.assertEqual(w.render('date', datetime.datetime(2006, 1, 10, 7, 30)), u'<input type="text" name="date_0" value="2006-01-10" /><input type="text" name="date_1" value="07:30:00" />')
        self.assertEqual(w.render('date', [datetime.date(2006, 1, 10), datetime.time(7, 30)]), u'<input type="text" name="date_0" value="2006-01-10" /><input type="text" name="date_1" value="07:30:00" />')

        # You can also pass 'attrs' to the constructor. In this case, the attrs will be
        w = SplitDateTimeWidget(attrs={'class': 'pretty'})
        self.assertEqual(w.render('date', datetime.datetime(2006, 1, 10, 7, 30)), u'<input type="text" class="pretty" value="2006-01-10" name="date_0" /><input type="text" class="pretty" value="07:30:00" name="date_1" />')

        # Use 'date_format' and 'time_format' to change the way a value is displayed.
        w = SplitDateTimeWidget(date_format='%d/%m/%Y', time_format='%H:%M')
        self.assertEqual(w.render('date', datetime.datetime(2006, 1, 10, 7, 30)), u'<input type="text" name="date_0" value="10/01/2006" /><input type="text" name="date_1" value="07:30" />')

        self.assertTrue(w._has_changed(datetime.datetime(2008, 5, 6, 12, 40, 00), [u'2008-05-06', u'12:40:00']))
        self.assertFalse(w._has_changed(datetime.datetime(2008, 5, 6, 12, 40, 00), [u'06/05/2008', u'12:40']))
        self.assertTrue(w._has_changed(datetime.datetime(2008, 5, 6, 12, 40, 00), [u'06/05/2008', u'12:41']))

    def test_datetimeinput(self):
        w = DateTimeInput()
        self.assertEqual(w.render('date', None), u'<input type="text" name="date" />')
        d = datetime.datetime(2007, 9, 17, 12, 51, 34, 482548)
        self.assertEqual(str(d), '2007-09-17 12:51:34.482548')

        # The microseconds are trimmed on display, by default.
        self.assertEqual(w.render('date', d), u'<input type="text" name="date" value="2007-09-17 12:51:34" />')
        self.assertEqual(w.render('date', datetime.datetime(2007, 9, 17, 12, 51, 34)), u'<input type="text" name="date" value="2007-09-17 12:51:34" />')
        self.assertEqual(w.render('date', datetime.datetime(2007, 9, 17, 12, 51)), u'<input type="text" name="date" value="2007-09-17 12:51:00" />')

        # Use 'format' to change the way a value is displayed.
        w = DateTimeInput(format='%d/%m/%Y %H:%M')
        self.assertEqual(w.render('date', d), u'<input type="text" name="date" value="17/09/2007 12:51" />')
        self.assertFalse(w._has_changed(d, '17/09/2007 12:51'))

        # Make sure a custom format works with _has_changed. The hidden input will use
        data = datetime.datetime(2010, 3, 6, 12, 0, 0)
        custom_format = '%d.%m.%Y %H:%M'
        w = DateTimeInput(format=custom_format)
        self.assertFalse(w._has_changed(formats.localize_input(data), data.strftime(custom_format)))

    def test_dateinput(self):
        w = DateInput()
        self.assertEqual(w.render('date', None), u'<input type="text" name="date" />')
        d = datetime.date(2007, 9, 17)
        self.assertEqual(str(d), '2007-09-17')

        self.assertEqual(w.render('date', d), u'<input type="text" name="date" value="2007-09-17" />')
        self.assertEqual(w.render('date', datetime.date(2007, 9, 17)), u'<input type="text" name="date" value="2007-09-17" />')

        # We should be able to initialize from a unicode value.
        self.assertEqual(w.render('date', u'2007-09-17'), u'<input type="text" name="date" value="2007-09-17" />')

        # Use 'format' to change the way a value is displayed.
        w = DateInput(format='%d/%m/%Y')
        self.assertEqual(w.render('date', d), u'<input type="text" name="date" value="17/09/2007" />')
        self.assertFalse(w._has_changed(d, '17/09/2007'))

        # Make sure a custom format works with _has_changed. The hidden input will use
        data = datetime.date(2010, 3, 6)
        custom_format = '%d.%m.%Y'
        w = DateInput(format=custom_format)
        self.assertFalse(w._has_changed(formats.localize_input(data), data.strftime(custom_format)))

    def test_timeinput(self):
        w = TimeInput()
        self.assertEqual(w.render('time', None), u'<input type="text" name="time" />')
        t = datetime.time(12, 51, 34, 482548)
        self.assertEqual(str(t), '12:51:34.482548')

        # The microseconds are trimmed on display, by default.
        self.assertEqual(w.render('time', t), u'<input type="text" name="time" value="12:51:34" />')
        self.assertEqual(w.render('time', datetime.time(12, 51, 34)), u'<input type="text" name="time" value="12:51:34" />')
        self.assertEqual(w.render('time', datetime.time(12, 51)), u'<input type="text" name="time" value="12:51:00" />')

        # We should be able to initialize from a unicode value.
        self.assertEqual(w.render('time', u'13:12:11'), u'<input type="text" name="time" value="13:12:11" />')

        # Use 'format' to change the way a value is displayed.
        w = TimeInput(format='%H:%M')
        self.assertEqual(w.render('time', t), u'<input type="text" name="time" value="12:51" />')
        self.assertFalse(w._has_changed(t, '12:51'))

        # Make sure a custom format works with _has_changed. The hidden input will use
        data = datetime.time(13, 0)
        custom_format = '%I:%M %p'
        w = TimeInput(format=custom_format)
        self.assertFalse(w._has_changed(formats.localize_input(data), data.strftime(custom_format)))

    def test_splithiddendatetime(self):
        from django.forms.widgets import SplitHiddenDateTimeWidget

        w = SplitHiddenDateTimeWidget()
        self.assertEqual(w.render('date', ''), u'<input type="hidden" name="date_0" /><input type="hidden" name="date_1" />')
        d = datetime.datetime(2007, 9, 17, 12, 51, 34, 482548)
        self.assertEqual(str(d), '2007-09-17 12:51:34.482548')
        self.assertEqual(w.render('date', d), u'<input type="hidden" name="date_0" value="2007-09-17" /><input type="hidden" name="date_1" value="12:51:34" />')
        self.assertEqual(w.render('date', datetime.datetime(2007, 9, 17, 12, 51, 34)), u'<input type="hidden" name="date_0" value="2007-09-17" /><input type="hidden" name="date_1" value="12:51:34" />')
        self.assertEqual(w.render('date', datetime.datetime(2007, 9, 17, 12, 51)), u'<input type="hidden" name="date_0" value="2007-09-17" /><input type="hidden" name="date_1" value="12:51:00" />')


class FormsI18NWidgetsTestCase(TestCase):
    def setUp(self):
        super(FormsI18NWidgetsTestCase, self).setUp()
        self.old_use_l10n = getattr(settings, 'USE_L10N', False)
        settings.USE_L10N = True
        activate('de-at')

    def tearDown(self):
        deactivate()
        settings.USE_L10N = self.old_use_l10n
        super(FormsI18NWidgetsTestCase, self).tearDown()

    def test_splitdatetime(self):
        w = SplitDateTimeWidget(date_format='%d/%m/%Y', time_format='%H:%M')
        self.assertTrue(w._has_changed(datetime.datetime(2008, 5, 6, 12, 40, 00), [u'06.05.2008', u'12:41']))

    def test_datetimeinput(self):
        w = DateTimeInput()
        d = datetime.datetime(2007, 9, 17, 12, 51, 34, 482548)
        w.is_localized = True
        self.assertEqual(w.render('date', d), u'<input type="text" name="date" value="17.09.2007 12:51:34" />')

    def test_dateinput(self):
        w = DateInput()
        d = datetime.date(2007, 9, 17)
        w.is_localized = True
        self.assertEqual(w.render('date', d), u'<input type="text" name="date" value="17.09.2007" />')

    def test_timeinput(self):
        w = TimeInput()
        t = datetime.time(12, 51, 34, 482548)
        w.is_localized = True
        self.assertEqual(w.render('time', t), u'<input type="text" name="time" value="12:51:34" />')

    def test_splithiddendatetime(self):
        from django.forms.widgets import SplitHiddenDateTimeWidget

        w = SplitHiddenDateTimeWidget()
        w.is_localized = True
        self.assertEqual(w.render('date', datetime.datetime(2007, 9, 17, 12, 51)), u'<input type="hidden" name="date_0" value="17.09.2007" /><input type="hidden" name="date_1" value="12:51:00" />')


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
        w1 = SelectAndTextWidget(choices=[1,2,3])
        w2 = copy.deepcopy(w1)
        w2.choices = [4,5,6]
        # w2 ought to be independent of w1, since MultiWidget ought
        # to make a copy of its sub-widgets when it is copied.
        self.assertEqual(w1.choices, [1,2,3])

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


class FakeFieldFile(object):
    """
    Quacks like a FieldFile (has a .url and unicode representation), but
    doesn't require us to care about storages etc.

    """
    url = 'something'

    def __unicode__(self):
        return self.url

class ClearableFileInputTests(TestCase):
    def test_clear_input_renders(self):
        """
        A ClearableFileInput with is_required False and rendered with
        an initial value that is a file renders a clear checkbox.

        """
        widget = ClearableFileInput()
        widget.is_required = False
        self.assertEqual(widget.render('myfile', FakeFieldFile()),
                         u'Currently: <a target="_blank" href="something">something</a> <input type="checkbox" name="myfile-clear" id="myfile-clear_id" /> <label for="myfile-clear_id">Clear</label><br />Change: <input type="file" name="myfile" />')

    def test_clear_input_renders_only_if_not_required(self):
        """
        A ClearableFileInput with is_required=False does not render a clear
        checkbox.

        """
        widget = ClearableFileInput()
        widget.is_required = True
        self.assertEqual(widget.render('myfile', FakeFieldFile()),
                         u'Currently: <a target="_blank" href="something">something</a> <br />Change: <input type="file" name="myfile" />')

    def test_clear_input_renders_only_if_initial(self):
        """
        A ClearableFileInput instantiated with no initial value does not render
        a clear checkbox.

        """
        widget = ClearableFileInput()
        widget.is_required = False
        self.assertEqual(widget.render('myfile', None),
                         u'<input type="file" name="myfile" />')

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
        f = SimpleUploadedFile('something.txt', 'content')
        self.assertEqual(widget.value_from_datadict(
                data={'myfile-clear': True},
                files={'myfile': f},
                name='myfile'), f)
