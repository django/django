from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.utils.translation import gettext_lazy as _


class AdminAuthenticationForm(AuthenticationForm):
    """
    A custom authentication form used in the admin app.
    """
    required_css_class = 'required'


class AdminPasswordChangeForm(PasswordChangeForm):
    required_css_class = 'required'
