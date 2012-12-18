from __future__ import unicode_literals

from django import forms

from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import ugettext_lazy

ERROR_MESSAGE = ugettext_lazy("Please enter the correct %(username)s and password "
        "for a staff account. Note that both fields may be case-sensitive.")


class AdminAuthenticationForm(AuthenticationForm):
    """
    A custom authentication form used in the admin app.

    """
    this_is_the_login_form = forms.BooleanField(widget=forms.HiddenInput, initial=1,
        error_messages={'required': ugettext_lazy("Please log in again, because your session has expired.")})

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        message = ERROR_MESSAGE

        if username and password:
            self.user_cache = authenticate(username=username, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(message % {
                    'username': self.username_field.verbose_name
                })
            elif not self.user_cache.is_active or not self.user_cache.is_staff:
                raise forms.ValidationError(message % {
                    'username': self.username_field.verbose_name
                })
        self.check_for_test_cookie()
        return self.cleaned_data
