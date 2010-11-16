# -*- coding: utf-8 -*-
import datetime
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.db import connection
from django.forms import Form, ModelForm, FileField, ModelChoiceField
from django.test import TestCase
from regressiontests.forms.models import ChoiceModel, ChoiceOptionModel, ChoiceFieldModel, FileModel, Group, BoundaryModel, Defaults


class ChoiceFieldForm(ModelForm):
    class Meta:
        model = ChoiceFieldModel


class FileForm(Form):
    file1 = FileField()


class TestTicket12510(TestCase):
    ''' It is not necessary to generate choices for ModelChoiceField (regression test for #12510). '''
    def setUp(self):
        self.groups = [Group.objects.create(name=name) for name in 'abc']
        self.old_debug = settings.DEBUG
        # turn debug on to get access to connection.queries
        settings.DEBUG = True

    def tearDown(self):
        settings.DEBUG = self.old_debug

    def test_choices_not_fetched_when_not_rendering(self):
        initial_queries = len(connection.queries)
        field = ModelChoiceField(Group.objects.order_by('-name'))
        self.assertEqual('a', field.clean(self.groups[0].pk).name)
        # only one query is required to pull the model from DB
        self.assertEqual(initial_queries+1, len(connection.queries))

class ModelFormCallableModelDefault(TestCase):
    def test_no_empty_option(self):
        "If a model's ForeignKey has blank=False and a default, no empty option is created (Refs #10792)."
        option = ChoiceOptionModel.objects.create(name='default')

        choices = list(ChoiceFieldForm().fields['choice'].choices)
        self.assertEquals(len(choices), 1)
        self.assertEquals(choices[0], (option.pk, unicode(option)))

    def test_callable_initial_value(self):
        "The initial value for a callable default returning a queryset is the pk (refs #13769)"
        obj1 = ChoiceOptionModel.objects.create(id=1, name='default')
        obj2 = ChoiceOptionModel.objects.create(id=2, name='option 2')
        obj3 = ChoiceOptionModel.objects.create(id=3, name='option 3')
        self.assertEquals(ChoiceFieldForm().as_p(), """<p><label for="id_choice">Choice:</label> <select name="choice" id="id_choice">
<option value="1" selected="selected">ChoiceOption 1</option>
<option value="2">ChoiceOption 2</option>
<option value="3">ChoiceOption 3</option>
</select><input type="hidden" name="initial-choice" value="1" id="initial-id_choice" /></p>
<p><label for="id_choice_int">Choice int:</label> <select name="choice_int" id="id_choice_int">
<option value="1" selected="selected">ChoiceOption 1</option>
<option value="2">ChoiceOption 2</option>
<option value="3">ChoiceOption 3</option>
</select><input type="hidden" name="initial-choice_int" value="1" id="initial-id_choice_int" /></p>
<p><label for="id_multi_choice">Multi choice:</label> <select multiple="multiple" name="multi_choice" id="id_multi_choice">
<option value="1" selected="selected">ChoiceOption 1</option>
<option value="2">ChoiceOption 2</option>
<option value="3">ChoiceOption 3</option>
</select><input type="hidden" name="initial-multi_choice" value="1" id="initial-id_multi_choice_0" />  Hold down "Control", or "Command" on a Mac, to select more than one.</p>
<p><label for="id_multi_choice_int">Multi choice int:</label> <select multiple="multiple" name="multi_choice_int" id="id_multi_choice_int">
<option value="1" selected="selected">ChoiceOption 1</option>
<option value="2">ChoiceOption 2</option>
<option value="3">ChoiceOption 3</option>
</select><input type="hidden" name="initial-multi_choice_int" value="1" id="initial-id_multi_choice_int_0" />  Hold down "Control", or "Command" on a Mac, to select more than one.</p>""")

    def test_initial_instance_value(self):
        "Initial instances for model fields may also be instances (refs #7287)"
        obj1 = ChoiceOptionModel.objects.create(id=1, name='default')
        obj2 = ChoiceOptionModel.objects.create(id=2, name='option 2')
        obj3 = ChoiceOptionModel.objects.create(id=3, name='option 3')
        self.assertEquals(ChoiceFieldForm(initial={
                'choice': obj2,
                'choice_int': obj2,
                'multi_choice': [obj2,obj3],
                'multi_choice_int': ChoiceOptionModel.objects.exclude(name="default"),
            }).as_p(), """<p><label for="id_choice">Choice:</label> <select name="choice" id="id_choice">
<option value="1">ChoiceOption 1</option>
<option value="2" selected="selected">ChoiceOption 2</option>
<option value="3">ChoiceOption 3</option>
</select><input type="hidden" name="initial-choice" value="2" id="initial-id_choice" /></p>
<p><label for="id_choice_int">Choice int:</label> <select name="choice_int" id="id_choice_int">
<option value="1">ChoiceOption 1</option>
<option value="2" selected="selected">ChoiceOption 2</option>
<option value="3">ChoiceOption 3</option>
</select><input type="hidden" name="initial-choice_int" value="2" id="initial-id_choice_int" /></p>
<p><label for="id_multi_choice">Multi choice:</label> <select multiple="multiple" name="multi_choice" id="id_multi_choice">
<option value="1">ChoiceOption 1</option>
<option value="2" selected="selected">ChoiceOption 2</option>
<option value="3" selected="selected">ChoiceOption 3</option>
</select><input type="hidden" name="initial-multi_choice" value="2" id="initial-id_multi_choice_0" />
<input type="hidden" name="initial-multi_choice" value="3" id="initial-id_multi_choice_1" />  Hold down "Control", or "Command" on a Mac, to select more than one.</p>
<p><label for="id_multi_choice_int">Multi choice int:</label> <select multiple="multiple" name="multi_choice_int" id="id_multi_choice_int">
<option value="1">ChoiceOption 1</option>
<option value="2" selected="selected">ChoiceOption 2</option>
<option value="3" selected="selected">ChoiceOption 3</option>
</select><input type="hidden" name="initial-multi_choice_int" value="2" id="initial-id_multi_choice_int_0" />
<input type="hidden" name="initial-multi_choice_int" value="3" id="initial-id_multi_choice_int_1" />  Hold down "Control", or "Command" on a Mac, to select more than one.</p>""")



class FormsModelTestCase(TestCase):
    def test_unicode_filename(self):
        # FileModel with unicode filename and data #########################
        f = FileForm(data={}, files={'file1': SimpleUploadedFile('我隻氣墊船裝滿晒鱔.txt', 'मेरी मँडराने वाली नाव सर्पमीनों से भरी ह')}, auto_id=False)
        self.assertTrue(f.is_valid())
        self.assertTrue('file1' in f.cleaned_data)
        m = FileModel.objects.create(file=f.cleaned_data['file1'])
        self.assertEqual(m.file.name, u'tests/\u6211\u96bb\u6c23\u588a\u8239\u88dd\u6eff\u6652\u9c54.txt')
        m.delete()

    def test_boundary_conditions(self):
        # Boundary conditions on a PostitiveIntegerField #########################
        class BoundaryForm(ModelForm):
            class Meta:
                model = BoundaryModel

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

        self.assertEqual(DefaultsForm().fields['name'].initial, u'class default value')
        self.assertEqual(DefaultsForm().fields['def_date'].initial, datetime.date(1980, 1, 1))
        self.assertEqual(DefaultsForm().fields['value'].initial, 42)
        r1 = DefaultsForm()['callable_default'].as_widget()
        r2 = DefaultsForm()['callable_default'].as_widget()
        self.assertNotEqual(r1, r2)

        # In a ModelForm that is passed an instance, the initial values come from the
        # instance's values, not the model's defaults.
        foo_instance = Defaults(name=u'instance value', def_date=datetime.date(1969, 4, 4), value=12)
        instance_form = DefaultsForm(instance=foo_instance)
        self.assertEqual(instance_form.initial['name'], u'instance value')
        self.assertEqual(instance_form.initial['def_date'], datetime.date(1969, 4, 4))
        self.assertEqual(instance_form.initial['value'], 12)

        from django.forms import CharField

        class ExcludingForm(ModelForm):
            name = CharField(max_length=255)

            class Meta:
                model = Defaults
                exclude = ['name', 'callable_default']

        f = ExcludingForm({'name': u'Hello', 'value': 99, 'def_date': datetime.date(1999, 3, 2)})
        self.assertTrue(f.is_valid())
        self.assertEqual(f.cleaned_data['name'], u'Hello')
        obj = f.save()
        self.assertEqual(obj.name, u'class default value')
        self.assertEqual(obj.value, 99)
        self.assertEqual(obj.def_date, datetime.date(1999, 3, 2))
