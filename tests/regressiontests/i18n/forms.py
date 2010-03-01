from django import template, forms
from django.forms.extras import SelectDateWidget
from models import Company

class I18nForm(forms.Form):
    decimal_field = forms.DecimalField()
    float_field = forms.FloatField()
    date_field = forms.DateField()
    datetime_field = forms.DateTimeField()
    time_field = forms.TimeField()
    integer_field = forms.IntegerField()

class SelectDateForm(forms.Form):
    date_field = forms.DateField(widget=SelectDateWidget)

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
