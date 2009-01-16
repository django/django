# -*- coding: utf-8 -*-
import datetime
import tempfile

from django.db import models
# Can't import as "forms" due to implementation details in the test suite (the
# current file is called "forms" and is already imported).
from django import forms as django_forms
from django.core.files.storage import FileSystemStorage

temp_storage_location = tempfile.mkdtemp()
temp_storage = FileSystemStorage(location=temp_storage_location)

class BoundaryModel(models.Model):
    positive_integer = models.PositiveIntegerField(null=True, blank=True)

class Defaults(models.Model):
    name = models.CharField(max_length=256, default='class default value')
    def_date = models.DateField(default = datetime.date(1980, 1, 1))
    value = models.IntegerField(default=42)

class ChoiceModel(models.Model):
    """For ModelChoiceField and ModelMultipleChoiceField tests."""
    name = models.CharField(max_length=10)

class FileModel(models.Model):
    file = models.FileField(storage=temp_storage, upload_to='tests')

class FileForm(django_forms.Form):
    file1 = django_forms.FileField()

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
"""}
