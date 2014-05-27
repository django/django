from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm


class CustomAdminAuthenticationForm(AdminAuthenticationForm):

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username == 'customform':
            raise forms.ValidationError('custom form error')
        return username


class CustomAdminAuthenticationForm2(AdminAuthenticationForm):

    def confirm_login_allowed(self, user):
        if not user.is_active or not user.specialprofile.special:
            raise forms.ValidationError(
                self.error_messages['invalid_login'],
                code='invalid_login',
                params={'username': self.username_field.verbose_name}
            )
