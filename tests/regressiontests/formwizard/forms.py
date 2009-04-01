from django import forms
from django.contrib.formtools.wizard import FormWizard
from django.http import HttpResponse

class Page1(forms.Form):
    name = forms.CharField(max_length=100)
    thirsty = forms.NullBooleanField()

class Page2(forms.Form):
    address1 = forms.CharField(max_length=100)
    address2 = forms.CharField(max_length=100)
    
class Page3(forms.Form):
    random_crap = forms.CharField(max_length=100)
    
class ContactWizard(FormWizard):
    def done(self, request, form_list):
        return HttpResponse("")
