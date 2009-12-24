from django import template, forms
from django.forms.extras import SelectDateWidget

class I18nForm(forms.Form):
    decimal_field = forms.DecimalField()
    float_field = forms.FloatField()
    date_field = forms.DateField()
    datetime_field = forms.DateTimeField()
    time_field = forms.TimeField()

class SelectDateForm(forms.Form):
    date_field = forms.DateField(widget=SelectDateWidget)

