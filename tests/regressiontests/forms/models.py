import datetime

from django.db import models

class BoundaryModel(models.Model):
    positive_integer = models.PositiveIntegerField(null=True, blank=True)

class Defaults(models.Model):
    name = models.CharField(max_length=256, default='class default value')
    def_date = models.DateField(default = datetime.date(1980, 1, 1))
    value = models.IntegerField(default=42)

class ChoiceModel(models.Model):
    """For ModelChoiceField and ModelMultipleChoiceField tests."""
    name = models.CharField(max_length=10)

__test__ = {'API_TESTS': """
>>> from django.forms import form_for_model, form_for_instance

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
