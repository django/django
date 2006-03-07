from django.contrib.auth.models import User
from django.core import validators
from django import forms

class AuthenticationForm(forms.Manipulator):
    """
    Base class for authenticating users. Extend this to get a form that accepts
    username/password logins.
    """
    def __init__(self, request=None):
        """
        If request is passed in, the manipulator will validate that cookies are
        enabled. Note that the request (a HttpRequest object) must have set a
        cookie with the key TEST_COOKIE_NAME and value TEST_COOKIE_VALUE before
        running this validator.
        """
        self.request = request
        self.fields = [
            forms.TextField(field_name="username", length=15, maxlength=30, is_required=True,
                validator_list=[self.isValidUser, self.hasCookiesEnabled]),
            forms.PasswordField(field_name="password", length=15, maxlength=30, is_required=True,
                validator_list=[self.isValidPasswordForUser]),
        ]
        self.user_cache = None

    def hasCookiesEnabled(self, field_data, all_data):
        if self.request and not self.request.session.test_cookie_worked():
            raise validators.ValidationError, _("Your Web browser doesn't appear to have cookies enabled. Cookies are required for logging in.")

    def isValidUser(self, field_data, all_data):
        try:
            self.user_cache = User.objects.get(username=field_data)
        except User.DoesNotExist:
            raise validators.ValidationError, _("Please enter a correct username and password. Note that both fields are case-sensitive.")

    def isValidPasswordForUser(self, field_data, all_data):
        if self.user_cache is not None and not self.user_cache.check_password(field_data):
            self.user_cache = None
            raise validators.ValidationError, _("Please enter a correct username and password. Note that both fields are case-sensitive.")

    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None

    def get_user(self):
        return self.user_cache
