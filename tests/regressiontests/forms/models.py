# -*- coding: utf-8 -*-
import datetime
import tempfile
import shutil

from django.db import models, connection
from django.conf import settings
# Can't import as "forms" due to implementation details in the test suite (the
# current file is called "forms" and is already imported).
from django import forms as django_forms
from django.core.files.storage import FileSystemStorage
from django.test import TestCase

temp_storage_location = tempfile.mkdtemp()
temp_storage = FileSystemStorage(location=temp_storage_location)

class BoundaryModel(models.Model):
    positive_integer = models.PositiveIntegerField(null=True, blank=True)

callable_default_value = 0
def callable_default():
    global callable_default_value
    callable_default_value = callable_default_value + 1
    return callable_default_value

class Defaults(models.Model):
    name = models.CharField(max_length=255, default='class default value')
    def_date = models.DateField(default = datetime.date(1980, 1, 1))
    value = models.IntegerField(default=42)
    callable_default = models.IntegerField(default=callable_default)

class ChoiceModel(models.Model):
    """For ModelChoiceField and ModelMultipleChoiceField tests."""
    name = models.CharField(max_length=10)

class ChoiceOptionModel(models.Model):
    """Destination for ChoiceFieldModel's ForeignKey.
    Can't reuse ChoiceModel because error_message tests require that it have no instances."""
    name = models.CharField(max_length=10)

class ChoiceFieldModel(models.Model):
    """Model with ForeignKey to another model, for testing ModelForm
    generation with ModelChoiceField."""
    choice = models.ForeignKey(ChoiceOptionModel, blank=False,
                               default=lambda: ChoiceOptionModel.objects.all()[0])

class FileModel(models.Model):
    file = models.FileField(storage=temp_storage, upload_to='tests')

class FileForm(django_forms.Form):
    file1 = django_forms.FileField()

class Group(models.Model):
    name = models.CharField(max_length=10)

    def __unicode__(self):
        return u'%s' % self.name

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
        field = django_forms.ModelChoiceField(Group.objects.order_by('-name'))
        self.assertEqual('a', field.clean(self.groups[0].pk).name)
        # only one query is required to pull the model from DB
        self.assertEqual(initial_queries+1, len(connection.queries))


__test__ = {'API_TESTS': """
>>> from django.forms.models import ModelForm
>>> from django.core.files.uploadedfile import SimpleUploadedFile

# FileModel with unicode filename and data #########################
>>> f = FileForm(data={}, files={'file1': SimpleUploadedFile('我隻氣墊船裝滿晒鱔.txt', 'मेरी मँडराने वाली नाव सर्पमीनों से भरी ह')}, auto_id=False)
>>> f.is_valid()
True
>>> f.cleaned_data
{'file1': <SimpleUploadedFile: 我隻氣墊船裝滿晒鱔.txt (text/plain)>}
>>> m = FileModel.objects.create(file=f.cleaned_data['file1'])

# It's enough that m gets created without error.  Preservation of the exotic name is checked
# in a file_uploads test; it's hard to do that correctly with doctest's unicode issues. So
# we create and then immediately delete m so as to not leave the exotically named file around
# for shutil.rmtree (on Windows) to have trouble with later.
>>> m.delete()

# Boundary conditions on a PostitiveIntegerField #########################
>>> class BoundaryForm(ModelForm):
...     class Meta:
...         model = BoundaryModel
>>> f = BoundaryForm({'positive_integer': 100})
>>> f.is_valid()
True
>>> f = BoundaryForm({'positive_integer': 0})
>>> f.is_valid()
True
>>> f = BoundaryForm({'positive_integer': -100})
>>> f.is_valid()
False

# Formfield initial values ########
If the model has default values for some fields, they are used as the formfield
initial values.
>>> class DefaultsForm(ModelForm):
...     class Meta:
...         model = Defaults
>>> DefaultsForm().fields['name'].initial
u'class default value'
>>> DefaultsForm().fields['def_date'].initial
datetime.date(1980, 1, 1)
>>> DefaultsForm().fields['value'].initial
42
>>> r1 = DefaultsForm()['callable_default'].as_widget()
>>> r2 = DefaultsForm()['callable_default'].as_widget()
>>> r1 == r2
False

In a ModelForm that is passed an instance, the initial values come from the
instance's values, not the model's defaults.
>>> foo_instance = Defaults(name=u'instance value', def_date=datetime.date(1969, 4, 4), value=12)
>>> instance_form = DefaultsForm(instance=foo_instance)
>>> instance_form.initial['name']
u'instance value'
>>> instance_form.initial['def_date']
datetime.date(1969, 4, 4)
>>> instance_form.initial['value']
12

>>> from django.forms import CharField
>>> class ExcludingForm(ModelForm):
...     name = CharField(max_length=255)
...     class Meta:
...         model = Defaults
...         exclude = ['name', 'callable_default']
>>> f = ExcludingForm({'name': u'Hello', 'value': 99, 'def_date': datetime.date(1999, 3, 2)})
>>> f.is_valid()
True
>>> f.cleaned_data['name']
u'Hello'
>>> obj = f.save()
>>> obj.name
u'class default value'
>>> obj.value
99
>>> obj.def_date
datetime.date(1999, 3, 2)
>>> shutil.rmtree(temp_storage_location)

In a ModelForm with a ModelChoiceField, if the model's ForeignKey has blank=False and a default,
no empty option is created (regression test for #10792).

First we need at least one instance of ChoiceOptionModel:

>>> ChoiceOptionModel.objects.create(name='default')
<ChoiceOptionModel: ChoiceOptionModel object>

>>> class ChoiceFieldForm(ModelForm):
...     class Meta:
...         model = ChoiceFieldModel
>>> list(ChoiceFieldForm().fields['choice'].choices)
[(1, u'ChoiceOptionModel object')]

"""}
