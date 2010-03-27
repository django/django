from django import template, forms
from django.forms.extras import SelectDateWidget
from models import Company

class I18nForm(forms.Form):
    decimal_field = forms.DecimalField(localize=True)
    float_field = forms.FloatField(localize=True)
    date_field = forms.DateField(localize=True)
    datetime_field = forms.DateTimeField(localize=True)
    time_field = forms.TimeField(localize=True)
    integer_field = forms.IntegerField(localize=True)

class SelectDateForm(forms.Form):
    date_field = forms.DateField(widget=SelectDateWidget)

class CompanyForm(forms.ModelForm):
    cents_payed = forms.DecimalField(max_digits=4, decimal_places=2, localize=True)
    products_delivered = forms.IntegerField(localize=True)

    class Meta:
        model = Company
