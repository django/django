# -*- coding: utf-8 -*-
import datetime

from django.db import models
# Can't import as "forms" due to implementation details in the test suite (the
# current file is called "forms" an is already imported).
from django import forms as django_forms

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
    file = models.FileField(upload_to='/')

class FileForm(django_forms.Form):
    file1 = django_forms.FileField()

__test__ = {'API_TESTS': """
>>> from django.forms import form_for_model, form_for_instance
>>> from django.core.files.uploadedfile import SimpleUploadedFile

# FileModel with unicode filename and data #########################
>>> f = FileForm(data={}, files={'file1': SimpleUploadedFile('我隻氣墊船裝滿晒鱔.txt', 'मेरी मँडराने वाली नाव सर्पमीनों से भरी ह')}, auto_id=False)
>>> f.is_valid()
True
>>> f.cleaned_data
{'file1': <SimpleUploadedFile: 我隻氣墊船裝滿晒鱔.txt (text/plain)>}
>>> m = FileModel.objects.create(file=f.cleaned_data['file1'])

# Boundary conditions on a PostitiveIntegerField #########################
>>> BoundaryForm = form_for_model(BoundaryModel)
>>> f = BoundaryForm({'positive_integer':100})
>>> f.is_valid()
True
>>> f = BoundaryForm({'positive_integer':0})
>>> f.is_valid()
True
>>> f = BoundaryForm({'positive_integer':-100})
>>> f.is_valid()
False

# Formfield initial values ########
If the model has default values for some fields, they are used as the formfield
initial values.
>>> DefaultsForm = form_for_model(Defaults)
>>> DefaultsForm().fields['name'].initial
u'class default value'
>>> DefaultsForm().fields['def_date'].initial
datetime.date(1980, 1, 1)
>>> DefaultsForm().fields['value'].initial
42

In form_for_instance(), the initial values come from the instance's values, not
the model's defaults.
>>> foo_instance = Defaults(name=u'instance value', def_date = datetime.date(1969, 4, 4), value = 12)
>>> InstanceForm = form_for_instance(foo_instance)
>>> InstanceForm().fields['name'].initial
u'instance value'
>>> InstanceForm().fields['def_date'].initial
datetime.date(1969, 4, 4)
>>> InstanceForm().fields['value'].initial
12
"""}
