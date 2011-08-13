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

class TestForm(forms.Form):
    field1 = forms.CharField()
    field1_ = forms.CharField()
    bool1 = forms.BooleanField(required=False)

class HashTestForm(forms.Form):
    name = forms.CharField()
    bio = forms.CharField()

class HashTestBlankForm(forms.Form):
    name = forms.CharField(required=False)
    bio = forms.CharField(required=False)

class WizardPageOneForm(forms.Form):
    field = forms.CharField()

class WizardPageTwoForm(forms.Form):
    field = forms.CharField()

class WizardPageTwoAlternativeForm(forms.Form):
    field = forms.CharField()

class WizardPageThreeForm(forms.Form):
    field = forms.CharField()
