# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.admin.tests import AdminSeleniumTestCase
from django.forms import (
    CheckboxSelectMultiple, ClearableFileInput, RadioSelect, TextInput,
)
from django.forms.widgets import (
    ChoiceFieldRenderer, ChoiceInput, RadioFieldRenderer,
)
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import six
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.safestring import SafeData

from ..models import Article


class FormsWidgetTests(SimpleTestCase):

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
            inp_set4.append(
                '%s %s %s %s %s' % (
                    inp.name,
                    inp.value,
                    inp.choice_value,
                    inp.choice_label,
                    inp.is_checked(),
                )
            )

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
        self.assertHTMLEqual(
            str(r[0]),
            '<label><input checked="checked" type="radio" name="beatle" value="J" /> John</label>'
        )
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
        self.assertHTMLEqual(
            w.render('beatle', 'G', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))),
            """<label><input type="radio" name="beatle" value="J" /> John</label><br />
<label><input type="radio" name="beatle" value="P" /> Paul</label><br />
<label><input checked="checked" type="radio" name="beatle" value="G" /> George</label><br />
<label><input type="radio" name="beatle" value="R" /> Ringo</label>"""
        )

        # Or you can use custom RadioSelect fields that use your custom renderer.
        class CustomRadioSelect(RadioSelect):
            renderer = MyRenderer
        w = CustomRadioSelect()
        self.assertHTMLEqual(
            w.render('beatle', 'G', choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))),
            """<label><input type="radio" name="beatle" value="J" /> John</label><br />
<label><input type="radio" name="beatle" value="P" /> Paul</label><br />
<label><input checked="checked" type="radio" name="beatle" value="G" /> George</label><br />
<label><input type="radio" name="beatle" value="R" /> Ringo</label>"""
        )

        # You can customize rendering with outer_html/inner_html renderer variables (#22950)
        class MyRenderer(RadioFieldRenderer):
            # str is just to test some Python 2 issue with bytestrings
            outer_html = str('<div{id_attr}>{content}</div>')
            inner_html = '<p>{choice_value}{sub_widgets}</p>'
        w = RadioSelect(renderer=MyRenderer)
        output = w.render('beatle', 'J',
                          choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo')),
                          attrs={'id': 'bar'})
        self.assertIsInstance(output, SafeData)
        self.assertHTMLEqual(
            output,
            """<div id="bar">
<p><label for="bar_0"><input checked="checked" type="radio" id="bar_0" value="J" name="beatle" /> John</label></p>
<p><label for="bar_1"><input type="radio" id="bar_1" value="P" name="beatle" /> Paul</label></p>
<p><label for="bar_2"><input type="radio" id="bar_2" value="G" name="beatle" /> George</label></p>
<p><label for="bar_3"><input type="radio" id="bar_3" value="R" name="beatle" /> Ringo</label></p>
</div>""")

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


@override_settings(ROOT_URLCONF='forms_tests.urls')
class LiveWidgetTests(AdminSeleniumTestCase):

    available_apps = ['forms_tests'] + AdminSeleniumTestCase.available_apps

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


class ClearableFileInputTests(SimpleTestCase):

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
