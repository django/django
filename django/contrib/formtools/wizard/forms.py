from django import forms

class ManagementForm(forms.Form):
    """
    ``ManagementForm`` is used to keep track of the current wizard step.
    """
    current_step = forms.CharField(widget=forms.HiddenInput)
