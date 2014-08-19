from django import forms
from django.utils.translation import ugettext as _


class ManagementForm(forms.Form):
    """
    ``ManagementForm`` is used to keep track of the current wizard step.
    """
    current_step = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, form_list=None, *args, **kwargs):
        super(ManagementForm, self).__init__(*args, **kwargs)
        self.form_list = form_list

    def clean_current_step(self):
        current_step = self.cleaned_data.get('current_step')
        if self.form_list is not None and current_step not in self.form_list:
            raise forms.ValidationError(
                _('Invalid wizard step submitted'),
                code='invalid_wizard_step'
            )
