import os
import tempfile

from django import forms
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.forms.formsets import formset_factory
from django.forms.models import modelformset_factory
from django.http import HttpResponse
from django.template import Template, Context

from django.contrib.auth.models import User

from django.contrib.formtools.wizard.views import WizardView

temp_storage_location = tempfile.mkdtemp(dir=os.environ.get('DJANGO_TEST_TEMP_DIR'))
temp_storage = FileSystemStorage(location=temp_storage_location)

class Page1(forms.Form):
    name = forms.CharField(max_length=100)
    user = forms.ModelChoiceField(queryset=User.objects.all())
    thirsty = forms.NullBooleanField()

class Page2(forms.Form):
    address1 = forms.CharField(max_length=100)
    address2 = forms.CharField(max_length=100)
    file1 = forms.FileField()

class Page3(forms.Form):
    random_crap = forms.CharField(max_length=100)

Page4 = formset_factory(Page3, extra=2)

class ContactWizard(WizardView):
    file_storage = temp_storage

    def done(self, form_list, **kwargs):
        c = Context({
            'form_list': [x.cleaned_data for x in form_list],
            'all_cleaned_data': self.get_all_cleaned_data(),
        })

        for form in self.form_list.keys():
            c[form] = self.get_cleaned_data_for_step(form)

        c['this_will_fail'] = self.get_cleaned_data_for_step('this_will_fail')
        return HttpResponse(Template('').render(c))

    def get_context_data(self, form, **kwargs):
        context = super(ContactWizard, self).get_context_data(form, **kwargs)
        if self.storage.current_step == 'form2':
            context.update({'another_var': True})
        return context

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email')

UserFormSet = modelformset_factory(User, form=UserForm)

class SessionContactWizard(ContactWizard):
    storage_name = 'django.contrib.formtools.wizard.storage.session.SessionStorage'

class CookieContactWizard(ContactWizard):
    storage_name = 'django.contrib.formtools.wizard.storage.cookie.CookieStorage'

