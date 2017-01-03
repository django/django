# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.forms import (
    CharField, FileField, Form, ModelChoiceField, ModelForm,
)
from django.forms.models import ModelFormMetaclass
from django.test import SimpleTestCase, TestCase
from django.utils import six

from ..models import (
    BoundaryModel, ChoiceFieldModel, ChoiceModel, ChoiceOptionModel, Defaults,
    FileModel, Group, OptionalMultiChoiceModel,
)


class ChoiceFieldForm(ModelForm):
    class Meta:
        model = ChoiceFieldModel
        fields = '__all__'


class OptionalMultiChoiceModelForm(ModelForm):
    class Meta:
        model = OptionalMultiChoiceModel
        fields = '__all__'


class ChoiceFieldExclusionForm(ModelForm):
    multi_choice = CharField(max_length=50)

    class Meta:
        exclude = ['multi_choice']
        model = ChoiceFieldModel


class EmptyCharLabelChoiceForm(ModelForm):
    class Meta:
        model = ChoiceModel
        fields = ['name', 'choice']


class EmptyIntegerLabelChoiceForm(ModelForm):
    class Meta:
        model = ChoiceModel
        fields = ['name', 'choice_integer']


class EmptyCharLabelNoneChoiceForm(ModelForm):
    class Meta:
        model = ChoiceModel
        fields = ['name', 'choice_string_w_none']


class FileForm(Form):
    file1 = FileField()


class TestModelChoiceField(TestCase):

    def test_choices_not_fetched_when_not_rendering(self):
        """
        Generating choices for ModelChoiceField should require 1 query (#12510).
        """
        self.groups = [Group.objects.create(name=name) for name in 'abc']
        # only one query is required to pull the model from DB
        with self.assertNumQueries(1):
            field = ModelChoiceField(Group.objects.order_by('-name'))
            self.assertEqual('a', field.clean(self.groups[0].pk).name)

    def test_queryset_manager(self):
        f = ModelChoiceField(ChoiceOptionModel.objects)
        choice = ChoiceOptionModel.objects.create(name="choice 1")
        self.assertEqual(list(f.choices), [('', '---------'), (choice.pk, str(choice))])


class TestTicket14567(TestCase):
    """
    The return values of ModelMultipleChoiceFields are QuerySets
    """
    def test_empty_queryset_return(self):
        "If a model's ManyToManyField has blank=True and is saved with no data, a queryset is returned."
        option = ChoiceOptionModel.objects.create(name='default')
        form = OptionalMultiChoiceModelForm({'multi_choice_optional': '', 'multi_choice': [option.pk]})
        self.assertTrue(form.is_valid())
        # The empty value is a QuerySet
        self.assertIsInstance(form.cleaned_data['multi_choice_optional'], models.query.QuerySet)
        # While we're at it, test whether a QuerySet is returned if there *is* a value.
        self.assertIsInstance(form.cleaned_data['multi_choice'], models.query.QuerySet)


class ModelFormCallableModelDefault(TestCase):
    def test_no_empty_option(self):
        "If a model's ForeignKey has blank=False and a default, no empty option is created (Refs #10792)."
        option = ChoiceOptionModel.objects.create(name='default')

        choices = list(ChoiceFieldForm().fields['choice'].choices)
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0], (option.pk, six.text_type(option)))

    def test_callable_initial_value(self):
        "The initial value for a callable default returning a queryset is the pk (refs #13769)"
        ChoiceOptionModel.objects.create(id=1, name='default')
        ChoiceOptionModel.objects.create(id=2, name='option 2')
        ChoiceOptionModel.objects.create(id=3, name='option 3')
        self.assertHTMLEqual(
            ChoiceFieldForm().as_p(),
            """<p><label for="id_choice">Choice:</label> <select name="choice" id="id_choice">
<option value="1" selected>ChoiceOption 1</option>
<option value="2">ChoiceOption 2</option>
<option value="3">ChoiceOption 3</option>
</select><input type="hidden" name="initial-choice" value="1" id="initial-id_choice" /></p>
<p><label for="id_choice_int">Choice int:</label> <select name="choice_int" id="id_choice_int">
<option value="1" selected>ChoiceOption 1</option>
<option value="2">ChoiceOption 2</option>
<option value="3">ChoiceOption 3</option>
</select><input type="hidden" name="initial-choice_int" value="1" id="initial-id_choice_int" /></p>
<p><label for="id_multi_choice">Multi choice:</label>
<select multiple="multiple" name="multi_choice" id="id_multi_choice" required>
<option value="1" selected>ChoiceOption 1</option>
<option value="2">ChoiceOption 2</option>
<option value="3">ChoiceOption 3</option>
</select><input type="hidden" name="initial-multi_choice" value="1" id="initial-id_multi_choice_0" /></p>
<p><label for="id_multi_choice_int">Multi choice int:</label>
<select multiple="multiple" name="multi_choice_int" id="id_multi_choice_int" required>
<option value="1" selected>ChoiceOption 1</option>
<option value="2">ChoiceOption 2</option>
<option value="3">ChoiceOption 3</option>
</select><input type="hidden" name="initial-multi_choice_int" value="1" id="initial-id_multi_choice_int_0" /></p>"""
        )

    def test_initial_instance_value(self):
        "Initial instances for model fields may also be instances (refs #7287)"
        ChoiceOptionModel.objects.create(id=1, name='default')
        obj2 = ChoiceOptionModel.objects.create(id=2, name='option 2')
        obj3 = ChoiceOptionModel.objects.create(id=3, name='option 3')
        self.assertHTMLEqual(
            ChoiceFieldForm(initial={
                'choice': obj2,
                'choice_int': obj2,
                'multi_choice': [obj2, obj3],
                'multi_choice_int': ChoiceOptionModel.objects.exclude(name="default"),
            }).as_p(),
            """<p><label for="id_choice">Choice:</label> <select name="choice" id="id_choice">
<option value="1">ChoiceOption 1</option>
<option value="2" selected>ChoiceOption 2</option>
<option value="3">ChoiceOption 3</option>
</select><input type="hidden" name="initial-choice" value="2" id="initial-id_choice" /></p>
<p><label for="id_choice_int">Choice int:</label> <select name="choice_int" id="id_choice_int">
<option value="1">ChoiceOption 1</option>
<option value="2" selected>ChoiceOption 2</option>
<option value="3">ChoiceOption 3</option>
</select><input type="hidden" name="initial-choice_int" value="2" id="initial-id_choice_int" /></p>
<p><label for="id_multi_choice">Multi choice:</label>
<select multiple="multiple" name="multi_choice" id="id_multi_choice" required>
<option value="1">ChoiceOption 1</option>
<option value="2" selected>ChoiceOption 2</option>
<option value="3" selected>ChoiceOption 3</option>
</select><input type="hidden" name="initial-multi_choice" value="2" id="initial-id_multi_choice_0" />
<input type="hidden" name="initial-multi_choice" value="3" id="initial-id_multi_choice_1" /></p>
<p><label for="id_multi_choice_int">Multi choice int:</label>
<select multiple="multiple" name="multi_choice_int" id="id_multi_choice_int" required>
<option value="1">ChoiceOption 1</option>
<option value="2" selected>ChoiceOption 2</option>
<option value="3" selected>ChoiceOption 3</option>
</select><input type="hidden" name="initial-multi_choice_int" value="2" id="initial-id_multi_choice_int_0" />
<input type="hidden" name="initial-multi_choice_int" value="3" id="initial-id_multi_choice_int_1" /></p>"""
        )


class FormsModelTestCase(TestCase):
    def test_unicode_filename(self):
        # FileModel with unicode filename and data #########################
        file1 = SimpleUploadedFile('我隻氣墊船裝滿晒鱔.txt', 'मेरी मँडराने वाली नाव सर्पमीनों से भरी ह'.encode('utf-8'))
        f = FileForm(data={}, files={'file1': file1}, auto_id=False)
        self.assertTrue(f.is_valid())
        self.assertIn('file1', f.cleaned_data)
        m = FileModel.objects.create(file=f.cleaned_data['file1'])
        self.assertEqual(m.file.name, 'tests/\u6211\u96bb\u6c23\u588a\u8239\u88dd\u6eff\u6652\u9c54.txt')
        m.delete()

    def test_boundary_conditions(self):
        # Boundary conditions on a PositiveIntegerField #########################
        class BoundaryForm(ModelForm):
            class Meta:
                model = BoundaryModel
                fields = '__all__'

        f = BoundaryForm({'positive_integer': 100})
        self.assertTrue(f.is_valid())
        f = BoundaryForm({'positive_integer': 0})
        self.assertTrue(f.is_valid())
        f = BoundaryForm({'positive_integer': -100})
        self.assertFalse(f.is_valid())

    def test_formfield_initial(self):
        # Formfield initial values ########
        # If the model has default values for some fields, they are used as the formfield
        # initial values.
        class DefaultsForm(ModelForm):
            class Meta:
                model = Defaults
                fields = '__all__'

        self.assertEqual(DefaultsForm().fields['name'].initial, 'class default value')
        self.assertEqual(DefaultsForm().fields['def_date'].initial, datetime.date(1980, 1, 1))
        self.assertEqual(DefaultsForm().fields['value'].initial, 42)
        r1 = DefaultsForm()['callable_default'].as_widget()
        r2 = DefaultsForm()['callable_default'].as_widget()
        self.assertNotEqual(r1, r2)

        # In a ModelForm that is passed an instance, the initial values come from the
        # instance's values, not the model's defaults.
        foo_instance = Defaults(name='instance value', def_date=datetime.date(1969, 4, 4), value=12)
        instance_form = DefaultsForm(instance=foo_instance)
        self.assertEqual(instance_form.initial['name'], 'instance value')
        self.assertEqual(instance_form.initial['def_date'], datetime.date(1969, 4, 4))
        self.assertEqual(instance_form.initial['value'], 12)

        from django.forms import CharField

        class ExcludingForm(ModelForm):
            name = CharField(max_length=255)

            class Meta:
                model = Defaults
                exclude = ['name', 'callable_default']

        f = ExcludingForm({'name': 'Hello', 'value': 99, 'def_date': datetime.date(1999, 3, 2)})
        self.assertTrue(f.is_valid())
        self.assertEqual(f.cleaned_data['name'], 'Hello')
        obj = f.save()
        self.assertEqual(obj.name, 'class default value')
        self.assertEqual(obj.value, 99)
        self.assertEqual(obj.def_date, datetime.date(1999, 3, 2))


class RelatedModelFormTests(SimpleTestCase):
    def test_invalid_loading_order(self):
        """
        Test for issue 10405
        """
        class A(models.Model):
            ref = models.ForeignKey("B", models.CASCADE)

        class Meta:
            model = A
            fields = '__all__'

        with self.assertRaises(ValueError):
            ModelFormMetaclass(str('Form'), (ModelForm,), {'Meta': Meta})

        class B(models.Model):
            pass

    def test_valid_loading_order(self):
        """
        Test for issue 10405
        """
        class C(models.Model):
            ref = models.ForeignKey("D", models.CASCADE)

        class D(models.Model):
            pass

        class Meta:
            model = C
            fields = '__all__'

        self.assertTrue(issubclass(ModelFormMetaclass(str('Form'), (ModelForm,), {'Meta': Meta}), ModelForm))


class ManyToManyExclusionTestCase(TestCase):
    def test_m2m_field_exclusion(self):
        # Issue 12337. save_instance should honor the passed-in exclude keyword.
        opt1 = ChoiceOptionModel.objects.create(id=1, name='default')
        opt2 = ChoiceOptionModel.objects.create(id=2, name='option 2')
        opt3 = ChoiceOptionModel.objects.create(id=3, name='option 3')
        initial = {
            'choice': opt1,
            'choice_int': opt1,
        }
        data = {
            'choice': opt2.pk,
            'choice_int': opt2.pk,
            'multi_choice': 'string data!',
            'multi_choice_int': [opt1.pk],
        }
        instance = ChoiceFieldModel.objects.create(**initial)
        instance.multi_choice.set([opt2, opt3])
        instance.multi_choice_int.set([opt2, opt3])
        form = ChoiceFieldExclusionForm(data=data, instance=instance)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['multi_choice'], data['multi_choice'])
        form.save()
        self.assertEqual(form.instance.choice.pk, data['choice'])
        self.assertEqual(form.instance.choice_int.pk, data['choice_int'])
        self.assertEqual(list(form.instance.multi_choice.all()), [opt2, opt3])
        self.assertEqual([obj.pk for obj in form.instance.multi_choice_int.all()], data['multi_choice_int'])


class EmptyLabelTestCase(TestCase):
    def test_empty_field_char(self):
        f = EmptyCharLabelChoiceForm()
        self.assertHTMLEqual(
            f.as_p(),
            """<p><label for="id_name">Name:</label> <input id="id_name" maxlength="10" name="name" type="text" required /></p>
<p><label for="id_choice">Choice:</label> <select id="id_choice" name="choice">
<option value="" selected>No Preference</option>
<option value="f">Foo</option>
<option value="b">Bar</option>
</select></p>"""
        )

    def test_empty_field_char_none(self):
        f = EmptyCharLabelNoneChoiceForm()
        self.assertHTMLEqual(
            f.as_p(),
            """<p><label for="id_name">Name:</label> <input id="id_name" maxlength="10" name="name" type="text" required /></p>
<p><label for="id_choice_string_w_none">Choice string w none:</label>
<select id="id_choice_string_w_none" name="choice_string_w_none">
<option value="" selected>No Preference</option>
<option value="f">Foo</option>
<option value="b">Bar</option>
</select></p>"""
        )

    def test_save_empty_label_forms(self):
        # Saving a form with a blank choice results in the expected
        # value being stored in the database.
        tests = [
            (EmptyCharLabelNoneChoiceForm, 'choice_string_w_none', None),
            (EmptyIntegerLabelChoiceForm, 'choice_integer', None),
            (EmptyCharLabelChoiceForm, 'choice', ''),
        ]

        for form, key, expected in tests:
            f = form({'name': 'some-key', key: ''})
            self.assertTrue(f.is_valid())
            m = f.save()
            self.assertEqual(expected, getattr(m, key))
            self.assertEqual('No Preference',
                             getattr(m, 'get_{}_display'.format(key))())

    def test_empty_field_integer(self):
        f = EmptyIntegerLabelChoiceForm()
        self.assertHTMLEqual(
            f.as_p(),
            """<p><label for="id_name">Name:</label> <input id="id_name" maxlength="10" name="name" type="text" required /></p>
<p><label for="id_choice_integer">Choice integer:</label>
<select id="id_choice_integer" name="choice_integer">
<option value="" selected>No Preference</option>
<option value="1">Foo</option>
<option value="2">Bar</option>
</select></p>"""
        )

    def test_get_display_value_on_none(self):
        m = ChoiceModel.objects.create(name='test', choice='', choice_integer=None)
        self.assertIsNone(m.choice_integer)
        self.assertEqual('No Preference', m.get_choice_integer_display())

    def test_html_rendering_of_prepopulated_models(self):
        none_model = ChoiceModel(name='none-test', choice_integer=None)
        f = EmptyIntegerLabelChoiceForm(instance=none_model)
        self.assertHTMLEqual(
            f.as_p(),
            """<p><label for="id_name">Name:</label>
<input id="id_name" maxlength="10" name="name" type="text" value="none-test" required /></p>
<p><label for="id_choice_integer">Choice integer:</label>
<select id="id_choice_integer" name="choice_integer">
<option value="" selected>No Preference</option>
<option value="1">Foo</option>
<option value="2">Bar</option>
</select></p>"""
        )

        foo_model = ChoiceModel(name='foo-test', choice_integer=1)
        f = EmptyIntegerLabelChoiceForm(instance=foo_model)
        self.assertHTMLEqual(
            f.as_p(),
            """<p><label for="id_name">Name:</label>
<input id="id_name" maxlength="10" name="name" type="text" value="foo-test" required /></p>
<p><label for="id_choice_integer">Choice integer:</label>
<select id="id_choice_integer" name="choice_integer">
<option value="">No Preference</option>
<option value="1" selected>Foo</option>
<option value="2">Bar</option>
</select></p>"""
        )
