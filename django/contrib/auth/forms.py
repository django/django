from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.template import Context, loader
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
        if self.user_cache is None:
            return
        if not self.user_cache.check_password(field_data):
            self.user_cache = None
            raise validators.ValidationError, _("Please enter a correct username and password. Note that both fields are case-sensitive.")
        elif not self.user_cache.is_active:
            raise validators.ValidationError, _("This account is inactive.")

    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None

    def get_user(self):
        return self.user_cache

class PasswordResetForm(forms.Manipulator):
    "A form that lets a user request a password reset"
    def __init__(self):
        self.fields = (
            forms.EmailField(field_name="email", length=40, is_required=True,
                validator_list=[self.isValidUserEmail]),
        )

    def isValidUserEmail(self, new_data, all_data):
        "Validates that a user exists with the given e-mail address"
        try:
            self.user_cache = User.objects.get(email__iexact=new_data)
        except User.DoesNotExist:
            raise validators.ValidationError, "That e-mail address doesn't have an associated user acount. Are you sure you've registered?"

    def save(self, domain_override=None):
        "Calculates a new password randomly and sends it to the user"
        from django.core.mail import send_mail
        new_pass = User.objects.make_random_password()
        self.user_cache.set_password(new_pass)
        self.user_cache.save()
        if not domain_override:
            current_site = Site.objects.get_current()
            site_name = current_site.name
            domain = current_site.domain
        else:
            site_name = domain = domain_override
        t = loader.get_template('registration/password_reset_email.html')
        c = {
            'new_password': new_pass,
            'email': self.user_cache.email,
            'domain': domain,
            'site_name': site_name,
            'user': self.user_cache,
        }
        send_mail('Password reset on %s' % site_name, t.render(Context(c)), None, [self.user_cache.email])

class PasswordChangeForm(forms.Manipulator):
    "A form that lets a user change his password."
    def __init__(self, user):
        self.user = user
        self.fields = (
            forms.PasswordField(field_name="old_password", length=30, maxlength=30, is_required=True,
                validator_list=[self.isValidOldPassword]),
            forms.PasswordField(field_name="new_password1", length=30, maxlength=30, is_required=True,
                validator_list=[validators.AlwaysMatchesOtherField('new_password2', "The two 'new password' fields didn't match.")]),
            forms.PasswordField(field_name="new_password2", length=30, maxlength=30, is_required=True),
        )

    def isValidOldPassword(self, new_data, all_data):
        "Validates that the old_password field is correct."
        if not self.user.check_password(new_data):
            raise validators.ValidationError, "Your old password was entered incorrectly. Please enter it again."

    def save(self, new_data):
        "Saves the new password."
        self.user.set_password(new_data['new_password1'])
        self.user.save()
