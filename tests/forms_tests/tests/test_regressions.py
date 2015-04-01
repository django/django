# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from forms_tests.models import Cheese

from django.forms import (
    CharField, ChoiceField, Form, HiddenInput, IntegerField, ModelForm,
    ModelMultipleChoiceField, MultipleChoiceField, RadioSelect, Select,
    TextInput,
)
from django.test import TestCase, ignore_warnings
from django.utils import translation
from django.utils.translation import gettext_lazy, ugettext_lazy


class FormsRegressionsTestCase(TestCase):
    def test_class(self):
        # Tests to prevent against recurrences of earlier bugs.
        extra_attrs = {'class': 'special'}

        class TestForm(Form):
            f1 = CharField(max_length=10, widget=TextInput(attrs=extra_attrs))
            f2 = CharField(widget=TextInput(attrs=extra_attrs))

        self.assertHTMLEqual(TestForm(auto_id=False).as_p(), '<p>F1: <input type="text" class="special" name="f1" maxlength="10" /></p>\n<p>F2: <input type="text" class="special" name="f2" /></p>')

    def test_regression_3600(self):
        # Tests for form i18n #
        # There were some problems with form translations in #3600

        class SomeForm(Form):
            username = CharField(max_length=10, label=ugettext_lazy('username'))

        f = SomeForm()
        self.assertHTMLEqual(f.as_p(), '<p><label for="id_username">username:</label> <input id="id_username" type="text" name="username" maxlength="10" /></p>')

        # Translations are done at rendering time, so multi-lingual apps can define forms)
        with translation.override('de'):
            self.assertHTMLEqual(f.as_p(), '<p><label for="id_username">Benutzername:</label> <input id="id_username" type="text" name="username" maxlength="10" /></p>')
        with translation.override('pl'):
            self.assertHTMLEqual(f.as_p(), '<p><label for="id_username">u\u017cytkownik:</label> <input id="id_username" type="text" name="username" maxlength="10" /></p>')

    def test_regression_5216(self):
        # There was some problems with form translations in #5216
        class SomeForm(Form):
            field_1 = CharField(max_length=10, label=ugettext_lazy('field_1'))
            field_2 = CharField(max_length=10, label=ugettext_lazy('field_2'), widget=TextInput(attrs={'id': 'field_2_id'}))

        f = SomeForm()
        self.assertHTMLEqual(f['field_1'].label_tag(), '<label for="id_field_1">field_1:</label>')
        self.assertHTMLEqual(f['field_2'].label_tag(), '<label for="field_2_id">field_2:</label>')

        # Unicode decoding problems...
        GENDERS = (('\xc5', 'En tied\xe4'), ('\xf8', 'Mies'), ('\xdf', 'Nainen'))

        class SomeForm(Form):
            somechoice = ChoiceField(choices=GENDERS, widget=RadioSelect(), label='\xc5\xf8\xdf')

        f = SomeForm()
        self.assertHTMLEqual(f.as_p(), '<p><label for="id_somechoice_0">\xc5\xf8\xdf:</label> <ul id="id_somechoice">\n<li><label for="id_somechoice_0"><input type="radio" id="id_somechoice_0" value="\xc5" name="somechoice" /> En tied\xe4</label></li>\n<li><label for="id_somechoice_1"><input type="radio" id="id_somechoice_1" value="\xf8" name="somechoice" /> Mies</label></li>\n<li><label for="id_somechoice_2"><input type="radio" id="id_somechoice_2" value="\xdf" name="somechoice" /> Nainen</label></li>\n</ul></p>')

        # Translated error messages used to be buggy.
        with translation.override('ru'):
            f = SomeForm({})
            self.assertHTMLEqual(f.as_p(), '<ul class="errorlist"><li>\u041e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u043e\u0435 \u043f\u043e\u043b\u0435.</li></ul>\n<p><label for="id_somechoice_0">\xc5\xf8\xdf:</label> <ul id="id_somechoice">\n<li><label for="id_somechoice_0"><input type="radio" id="id_somechoice_0" value="\xc5" name="somechoice" /> En tied\xe4</label></li>\n<li><label for="id_somechoice_1"><input type="radio" id="id_somechoice_1" value="\xf8" name="somechoice" /> Mies</label></li>\n<li><label for="id_somechoice_2"><input type="radio" id="id_somechoice_2" value="\xdf" name="somechoice" /> Nainen</label></li>\n</ul></p>')

        # Deep copying translated text shouldn't raise an error)
        class CopyForm(Form):
            degree = IntegerField(widget=Select(choices=((1, gettext_lazy('test')),)))

        f = CopyForm()

    @ignore_warnings(category=UnicodeWarning)
    def test_regression_5216_b(self):
        # Testing choice validation with UTF-8 bytestrings as input (these are the
        # Russian abbreviations "мес." and "шт.".
        UNITS = ((b'\xd0\xbc\xd0\xb5\xd1\x81.', b'\xd0\xbc\xd0\xb5\xd1\x81.'),
                 (b'\xd1\x88\xd1\x82.', b'\xd1\x88\xd1\x82.'))
        f = ChoiceField(choices=UNITS)
        self.assertEqual(f.clean('\u0448\u0442.'), '\u0448\u0442.')
        self.assertEqual(f.clean(b'\xd1\x88\xd1\x82.'), '\u0448\u0442.')

    def test_misc(self):
        # There once was a problem with Form fields called "data". Let's make sure that
        # doesn't come back.
        class DataForm(Form):
            data = CharField(max_length=10)

        f = DataForm({'data': 'xyzzy'})
        self.assertTrue(f.is_valid())
        self.assertEqual(f.cleaned_data, {'data': 'xyzzy'})

        # A form with *only* hidden fields that has errors is going to be very unusual.
        class HiddenForm(Form):
            data = IntegerField(widget=HiddenInput)

        f = HiddenForm({})
        self.assertHTMLEqual(f.as_p(), '<ul class="errorlist nonfield"><li>(Hidden field data) This field is required.</li></ul>\n<p> <input type="hidden" name="data" id="id_data" /></p>')
        self.assertHTMLEqual(f.as_table(), '<tr><td colspan="2"><ul class="errorlist nonfield"><li>(Hidden field data) This field is required.</li></ul><input type="hidden" name="data" id="id_data" /></td></tr>')

    def test_xss_error_messages(self):
        ###################################################
        # Tests for XSS vulnerabilities in error messages #
        ###################################################

        # The forms layer doesn't escape input values directly because error messages
        # might be presented in non-HTML contexts. Instead, the message is just marked
        # for escaping by the template engine. So we'll need to construct a little
        # silly template to trigger the escaping.
        from django.template import Template, Context
        t = Template('{{ form.errors }}')

        class SomeForm(Form):
            field = ChoiceField(choices=[('one', 'One')])

        f = SomeForm({'field': '<script>'})
        self.assertHTMLEqual(t.render(Context({'form': f})), '<ul class="errorlist"><li>field<ul class="errorlist"><li>Select a valid choice. &lt;script&gt; is not one of the available choices.</li></ul></li></ul>')

        class SomeForm(Form):
            field = MultipleChoiceField(choices=[('one', 'One')])

        f = SomeForm({'field': ['<script>']})
        self.assertHTMLEqual(t.render(Context({'form': f})), '<ul class="errorlist"><li>field<ul class="errorlist"><li>Select a valid choice. &lt;script&gt; is not one of the available choices.</li></ul></li></ul>')

        from forms_tests.models import ChoiceModel

        class SomeForm(Form):
            field = ModelMultipleChoiceField(ChoiceModel.objects.all())

        f = SomeForm({'field': ['<script>']})
        self.assertHTMLEqual(t.render(Context({'form': f})), '<ul class="errorlist"><li>field<ul class="errorlist"><li>&quot;&lt;script&gt;&quot; is not a valid value for a primary key.</li></ul></li></ul>')

    def test_regression_14234(self):
        """
        Re-cleaning an instance that was added via a ModelForm should not raise
        a pk uniqueness error.

        """
        class CheeseForm(ModelForm):
            class Meta:
                model = Cheese
                fields = '__all__'

        form = CheeseForm({
            'name': 'Brie',
        })

        self.assertTrue(form.is_valid())

        obj = form.save()
        obj.name = 'Camembert'
        obj.full_clean()
