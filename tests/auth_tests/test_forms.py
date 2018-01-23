import datetime
import re
from unittest import mock

from django import forms
from django.contrib.auth.forms import (
    AdminPasswordChangeForm, AuthenticationForm, PasswordChangeForm,
    PasswordResetForm, ReadOnlyPasswordHashField, ReadOnlyPasswordHashWidget,
    SetPasswordForm, UserChangeForm, UserCreationForm,
)
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_login_failed
from django.contrib.sites.models import Site
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.forms.fields import CharField, Field, IntegerField
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import translation
from django.utils.text import capfirst
from django.utils.translation import gettext as _

from .models.custom_user import (
    CustomUser, CustomUserWithoutIsActiveField, ExtensionUser,
)
from .models.with_custom_email_field import CustomEmailField
from .models.with_integer_username import IntegerUsernameUser
from .settings import AUTH_TEMPLATES


class TestDataMixin:

    @classmethod
    def setUpTestData(cls):
        cls.u1 = User.objects.create_user(username='testclient', password='password', email='testclient@example.com')
        cls.u2 = User.objects.create_user(username='inactive', password='password', is_active=False)
        cls.u3 = User.objects.create_user(username='staff', password='password')
        cls.u4 = User.objects.create(username='empty_password', password='')
        cls.u5 = User.objects.create(username='unmanageable_password', password='$')
        cls.u6 = User.objects.create(username='unknown_password', password='foo$bar')


class UserCreationFormTest(TestDataMixin, TestCase):

    def test_user_already_exists(self):
        data = {
            'username': 'testclient',
            'password1': 'test123',
            'password2': 'test123',
        }
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["username"].errors,
                         [str(User._meta.get_field('username').error_messages['unique'])])

    def test_invalid_data(self):
        data = {
            'username': 'jsmith!',
            'password1': 'test123',
            'password2': 'test123',
        }
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        validator = next(v for v in User._meta.get_field('username').validators if v.code == 'invalid')
        self.assertEqual(form["username"].errors, [str(validator.message)])

    def test_password_verification(self):
        # The verification password is incorrect.
        data = {
            'username': 'jsmith',
            'password1': 'test123',
            'password2': 'test',
        }
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["password2"].errors,
                         [str(form.error_messages['password_mismatch'])])

    def test_both_passwords(self):
        # One (or both) passwords weren't given
        data = {'username': 'jsmith'}
        form = UserCreationForm(data)
        required_error = [str(Field.default_error_messages['required'])]
        self.assertFalse(form.is_valid())
        self.assertEqual(form['password1'].errors, required_error)
        self.assertEqual(form['password2'].errors, required_error)

        data['password2'] = 'test123'
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form['password1'].errors, required_error)
        self.assertEqual(form['password2'].errors, [])

    @mock.patch('django.contrib.auth.password_validation.password_changed')
    def test_success(self, password_changed):
        # The success case.
        data = {
            'username': 'jsmith@example.com',
            'password1': 'test123',
            'password2': 'test123',
        }
        form = UserCreationForm(data)
        self.assertTrue(form.is_valid())
        form.save(commit=False)
        self.assertEqual(password_changed.call_count, 0)
        u = form.save()
        self.assertEqual(password_changed.call_count, 1)
        self.assertEqual(repr(u), '<User: jsmith@example.com>')

    def test_unicode_username(self):
        data = {
            'username': '宝',
            'password1': 'test123',
            'password2': 'test123',
        }
        form = UserCreationForm(data)
        self.assertTrue(form.is_valid())
        u = form.save()
        self.assertEqual(u.username, '宝')

    def test_normalize_username(self):
        # The normalization happens in AbstractBaseUser.clean() and ModelForm
        # validation calls Model.clean().
        ohm_username = 'testΩ'  # U+2126 OHM SIGN
        data = {
            'username': ohm_username,
            'password1': 'pwd2',
            'password2': 'pwd2',
        }
        form = UserCreationForm(data)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertNotEqual(user.username, ohm_username)
        self.assertEqual(user.username, 'testΩ')  # U+03A9 GREEK CAPITAL LETTER OMEGA

    def test_duplicate_normalized_unicode(self):
        """
        To prevent almost identical usernames, visually identical but differing
        by their unicode code points only, Unicode NFKC normalization should
        make appear them equal to Django.
        """
        omega_username = 'iamtheΩ'  # U+03A9 GREEK CAPITAL LETTER OMEGA
        ohm_username = 'iamtheΩ'  # U+2126 OHM SIGN
        self.assertNotEqual(omega_username, ohm_username)
        User.objects.create_user(username=omega_username, password='pwd')
        data = {
            'username': ohm_username,
            'password1': 'pwd2',
            'password2': 'pwd2',
        }
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['username'], ["A user with that username already exists."]
        )

    @override_settings(AUTH_PASSWORD_VALIDATORS=[
        {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
        {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {
            'min_length': 12,
        }},
    ])
    def test_validates_password(self):
        data = {
            'username': 'testclient',
            'password1': 'testclient',
            'password2': 'testclient',
        }
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form['password2'].errors), 2)
        self.assertIn('The password is too similar to the username.', form['password2'].errors)
        self.assertIn(
            'This password is too short. It must contain at least 12 characters.',
            form['password2'].errors
        )

    def test_custom_form(self):
        class CustomUserCreationForm(UserCreationForm):
            class Meta(UserCreationForm.Meta):
                model = ExtensionUser
                fields = UserCreationForm.Meta.fields + ('date_of_birth',)

        data = {
            'username': 'testclient',
            'password1': 'testclient',
            'password2': 'testclient',
            'date_of_birth': '1988-02-24',
        }
        form = CustomUserCreationForm(data)
        self.assertTrue(form.is_valid())

    def test_custom_form_with_different_username_field(self):
        class CustomUserCreationForm(UserCreationForm):
            class Meta(UserCreationForm.Meta):
                model = CustomUser
                fields = ('email', 'date_of_birth')

        data = {
            'email': 'test@client222.com',
            'password1': 'testclient',
            'password2': 'testclient',
            'date_of_birth': '1988-02-24',
        }
        form = CustomUserCreationForm(data)
        self.assertTrue(form.is_valid())

    def test_custom_form_hidden_username_field(self):
        class CustomUserCreationForm(UserCreationForm):
            class Meta(UserCreationForm.Meta):
                model = CustomUserWithoutIsActiveField
                fields = ('email',)  # without USERNAME_FIELD

        data = {
            'email': 'testclient@example.com',
            'password1': 'testclient',
            'password2': 'testclient',
        }
        form = CustomUserCreationForm(data)
        self.assertTrue(form.is_valid())

    def test_password_whitespace_not_stripped(self):
        data = {
            'username': 'testuser',
            'password1': '   testpassword   ',
            'password2': '   testpassword   ',
        }
        form = UserCreationForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['password1'], data['password1'])
        self.assertEqual(form.cleaned_data['password2'], data['password2'])

    @override_settings(AUTH_PASSWORD_VALIDATORS=[
        {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    ])
    def test_password_help_text(self):
        form = UserCreationForm()
        self.assertEqual(
            form.fields['password1'].help_text,
            '<ul><li>Your password can&#39;t be too similar to your other personal information.</li></ul>'
        )

    @override_settings(AUTH_PASSWORD_VALIDATORS=[
        {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    ])
    def test_user_create_form_validates_password_with_all_data(self):
        """UserCreationForm password validation uses all of the form's data."""
        class CustomUserCreationForm(UserCreationForm):
            class Meta(UserCreationForm.Meta):
                model = User
                fields = ('username', 'email', 'first_name', 'last_name')
        form = CustomUserCreationForm({
            'username': 'testuser',
            'password1': 'testpassword',
            'password2': 'testpassword',
            'first_name': 'testpassword',
            'last_name': 'lastname',
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['password2'],
            ['The password is too similar to the first name.'],
        )


# To verify that the login form rejects inactive users, use an authentication
# backend that allows them.
@override_settings(AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.AllowAllUsersModelBackend'])
class AuthenticationFormTest(TestDataMixin, TestCase):

    def test_invalid_username(self):
        # The user submits an invalid username.

        data = {
            'username': 'jsmith_does_not_exist',
            'password': 'test123',
        }
        form = AuthenticationForm(None, data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.non_field_errors(), [
                form.error_messages['invalid_login'] % {
                    'username': User._meta.get_field('username').verbose_name
                }
            ]
        )

    def test_inactive_user(self):
        # The user is inactive.
        data = {
            'username': 'inactive',
            'password': 'password',
        }
        form = AuthenticationForm(None, data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(), [str(form.error_messages['inactive'])])

    # Use an authentication backend that rejects inactive users.
    @override_settings(AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.ModelBackend'])
    def test_inactive_user_incorrect_password(self):
        """An invalid login doesn't leak the inactive status of a user."""
        data = {
            'username': 'inactive',
            'password': 'incorrect',
        }
        form = AuthenticationForm(None, data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.non_field_errors(), [
                form.error_messages['invalid_login'] % {
                    'username': User._meta.get_field('username').verbose_name
                }
            ]
        )

    def test_login_failed(self):
        signal_calls = []

        def signal_handler(**kwargs):
            signal_calls.append(kwargs)

        user_login_failed.connect(signal_handler)
        fake_request = object()
        try:
            form = AuthenticationForm(fake_request, {
                'username': 'testclient',
                'password': 'incorrect',
            })
            self.assertFalse(form.is_valid())
            self.assertIs(signal_calls[0]['request'], fake_request)
        finally:
            user_login_failed.disconnect(signal_handler)

    def test_inactive_user_i18n(self):
        with self.settings(USE_I18N=True), translation.override('pt-br', deactivate=True):
            # The user is inactive.
            data = {
                'username': 'inactive',
                'password': 'password',
            }
            form = AuthenticationForm(None, data)
            self.assertFalse(form.is_valid())
            self.assertEqual(form.non_field_errors(), [str(form.error_messages['inactive'])])

    # Use an authentication backend that allows inactive users.
    @override_settings(AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.AllowAllUsersModelBackend'])
    def test_custom_login_allowed_policy(self):
        # The user is inactive, but our custom form policy allows them to log in.
        data = {
            'username': 'inactive',
            'password': 'password',
        }

        class AuthenticationFormWithInactiveUsersOkay(AuthenticationForm):
            def confirm_login_allowed(self, user):
                pass

        form = AuthenticationFormWithInactiveUsersOkay(None, data)
        self.assertTrue(form.is_valid())

        # If we want to disallow some logins according to custom logic,
        # we should raise a django.forms.ValidationError in the form.
        class PickyAuthenticationForm(AuthenticationForm):
            def confirm_login_allowed(self, user):
                if user.username == "inactive":
                    raise forms.ValidationError("This user is disallowed.")
                raise forms.ValidationError("Sorry, nobody's allowed in.")

        form = PickyAuthenticationForm(None, data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(), ['This user is disallowed.'])

        data = {
            'username': 'testclient',
            'password': 'password',
        }
        form = PickyAuthenticationForm(None, data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(), ["Sorry, nobody's allowed in."])

    def test_success(self):
        # The success case
        data = {
            'username': 'testclient',
            'password': 'password',
        }
        form = AuthenticationForm(None, data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.non_field_errors(), [])

    def test_unicode_username(self):
        User.objects.create_user(username='Σαρα', password='pwd')
        data = {
            'username': 'Σαρα',
            'password': 'pwd',
        }
        form = AuthenticationForm(None, data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.non_field_errors(), [])

    def test_username_field_label(self):

        class CustomAuthenticationForm(AuthenticationForm):
            username = CharField(label="Name", max_length=75)

        form = CustomAuthenticationForm()
        self.assertEqual(form['username'].label, "Name")

    def test_username_field_label_not_set(self):

        class CustomAuthenticationForm(AuthenticationForm):
            username = CharField()

        form = CustomAuthenticationForm()
        username_field = User._meta.get_field(User.USERNAME_FIELD)
        self.assertEqual(form.fields['username'].label, capfirst(username_field.verbose_name))

    def test_username_field_label_empty_string(self):

        class CustomAuthenticationForm(AuthenticationForm):
            username = CharField(label='')

        form = CustomAuthenticationForm()
        self.assertEqual(form.fields['username'].label, "")

    def test_password_whitespace_not_stripped(self):
        data = {
            'username': 'testuser',
            'password': ' pass ',
        }
        form = AuthenticationForm(None, data)
        form.is_valid()  # Not necessary to have valid credentails for the test.
        self.assertEqual(form.cleaned_data['password'], data['password'])

    @override_settings(AUTH_USER_MODEL='auth_tests.IntegerUsernameUser')
    def test_integer_username(self):
        class CustomAuthenticationForm(AuthenticationForm):
            username = IntegerField()

        user = IntegerUsernameUser.objects.create_user(username=0, password='pwd')
        data = {
            'username': 0,
            'password': 'pwd',
        }
        form = CustomAuthenticationForm(None, data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['username'], data['username'])
        self.assertEqual(form.cleaned_data['password'], data['password'])
        self.assertEqual(form.errors, {})
        self.assertEqual(form.user_cache, user)


class SetPasswordFormTest(TestDataMixin, TestCase):

    def test_password_verification(self):
        # The two new passwords do not match.
        user = User.objects.get(username='testclient')
        data = {
            'new_password1': 'abc123',
            'new_password2': 'abc',
        }
        form = SetPasswordForm(user, data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form["new_password2"].errors,
            [str(form.error_messages['password_mismatch'])]
        )

    @mock.patch('django.contrib.auth.password_validation.password_changed')
    def test_success(self, password_changed):
        user = User.objects.get(username='testclient')
        data = {
            'new_password1': 'abc123',
            'new_password2': 'abc123',
        }
        form = SetPasswordForm(user, data)
        self.assertTrue(form.is_valid())
        form.save(commit=False)
        self.assertEqual(password_changed.call_count, 0)
        form.save()
        self.assertEqual(password_changed.call_count, 1)

    @override_settings(AUTH_PASSWORD_VALIDATORS=[
        {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
        {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {
            'min_length': 12,
        }},
    ])
    def test_validates_password(self):
        user = User.objects.get(username='testclient')
        data = {
            'new_password1': 'testclient',
            'new_password2': 'testclient',
        }
        form = SetPasswordForm(user, data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form["new_password2"].errors), 2)
        self.assertIn('The password is too similar to the username.', form["new_password2"].errors)
        self.assertIn(
            'This password is too short. It must contain at least 12 characters.',
            form["new_password2"].errors
        )

    def test_password_whitespace_not_stripped(self):
        user = User.objects.get(username='testclient')
        data = {
            'new_password1': '   password   ',
            'new_password2': '   password   ',
        }
        form = SetPasswordForm(user, data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['new_password1'], data['new_password1'])
        self.assertEqual(form.cleaned_data['new_password2'], data['new_password2'])

    @override_settings(AUTH_PASSWORD_VALIDATORS=[
        {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
        {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {
            'min_length': 12,
        }},
    ])
    def test_help_text_translation(self):
        french_help_texts = [
            'Votre mot de passe ne peut pas trop ressembler à vos autres informations personnelles.',
            'Votre mot de passe doit contenir au minimum 12 caractères.',
        ]
        form = SetPasswordForm(self.u1)
        with translation.override('fr'):
            html = form.as_p()
            for french_text in french_help_texts:
                self.assertIn(french_text, html)


class PasswordChangeFormTest(TestDataMixin, TestCase):

    def test_incorrect_password(self):
        user = User.objects.get(username='testclient')
        data = {
            'old_password': 'test',
            'new_password1': 'abc123',
            'new_password2': 'abc123',
        }
        form = PasswordChangeForm(user, data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["old_password"].errors, [str(form.error_messages['password_incorrect'])])

    def test_password_verification(self):
        # The two new passwords do not match.
        user = User.objects.get(username='testclient')
        data = {
            'old_password': 'password',
            'new_password1': 'abc123',
            'new_password2': 'abc',
        }
        form = PasswordChangeForm(user, data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["new_password2"].errors, [str(form.error_messages['password_mismatch'])])

    @mock.patch('django.contrib.auth.password_validation.password_changed')
    def test_success(self, password_changed):
        # The success case.
        user = User.objects.get(username='testclient')
        data = {
            'old_password': 'password',
            'new_password1': 'abc123',
            'new_password2': 'abc123',
        }
        form = PasswordChangeForm(user, data)
        self.assertTrue(form.is_valid())
        form.save(commit=False)
        self.assertEqual(password_changed.call_count, 0)
        form.save()
        self.assertEqual(password_changed.call_count, 1)

    def test_field_order(self):
        # Regression test - check the order of fields:
        user = User.objects.get(username='testclient')
        self.assertEqual(list(PasswordChangeForm(user, {}).fields), ['old_password', 'new_password1', 'new_password2'])

    def test_password_whitespace_not_stripped(self):
        user = User.objects.get(username='testclient')
        user.set_password('   oldpassword   ')
        data = {
            'old_password': '   oldpassword   ',
            'new_password1': ' pass ',
            'new_password2': ' pass ',
        }
        form = PasswordChangeForm(user, data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['old_password'], data['old_password'])
        self.assertEqual(form.cleaned_data['new_password1'], data['new_password1'])
        self.assertEqual(form.cleaned_data['new_password2'], data['new_password2'])


class UserChangeFormTest(TestDataMixin, TestCase):

    def test_username_validity(self):
        user = User.objects.get(username='testclient')
        data = {'username': 'not valid'}
        form = UserChangeForm(data, instance=user)
        self.assertFalse(form.is_valid())
        validator = next(v for v in User._meta.get_field('username').validators if v.code == 'invalid')
        self.assertEqual(form["username"].errors, [str(validator.message)])

    def test_bug_14242(self):
        # A regression test, introduce by adding an optimization for the
        # UserChangeForm.

        class MyUserForm(UserChangeForm):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields['groups'].help_text = 'These groups give users different permissions'

            class Meta(UserChangeForm.Meta):
                fields = ('groups',)

        # Just check we can create it
        MyUserForm({})

    def test_unusable_password(self):
        user = User.objects.get(username='empty_password')
        user.set_unusable_password()
        user.save()
        form = UserChangeForm(instance=user)
        self.assertIn(_("No password set."), form.as_table())

    def test_bug_17944_empty_password(self):
        user = User.objects.get(username='empty_password')
        form = UserChangeForm(instance=user)
        self.assertIn(_("No password set."), form.as_table())

    def test_bug_17944_unmanageable_password(self):
        user = User.objects.get(username='unmanageable_password')
        form = UserChangeForm(instance=user)
        self.assertIn(_("Invalid password format or unknown hashing algorithm."), form.as_table())

    def test_bug_17944_unknown_password_algorithm(self):
        user = User.objects.get(username='unknown_password')
        form = UserChangeForm(instance=user)
        self.assertIn(_("Invalid password format or unknown hashing algorithm."), form.as_table())

    def test_bug_19133(self):
        "The change form does not return the password value"
        # Use the form to construct the POST data
        user = User.objects.get(username='testclient')
        form_for_data = UserChangeForm(instance=user)
        post_data = form_for_data.initial

        # The password field should be readonly, so anything
        # posted here should be ignored; the form will be
        # valid, and give back the 'initial' value for the
        # password field.
        post_data['password'] = 'new password'
        form = UserChangeForm(instance=user, data=post_data)

        self.assertTrue(form.is_valid())
        # original hashed password contains $
        self.assertIn('$', form.cleaned_data['password'])

    def test_bug_19349_bound_password_field(self):
        user = User.objects.get(username='testclient')
        form = UserChangeForm(data={}, instance=user)
        # When rendering the bound password field,
        # ReadOnlyPasswordHashWidget needs the initial
        # value to render correctly
        self.assertEqual(form.initial['password'], form['password'].value())

    def test_custom_form(self):
        class CustomUserChangeForm(UserChangeForm):
            class Meta(UserChangeForm.Meta):
                model = ExtensionUser
                fields = ('username', 'password', 'date_of_birth',)

        user = User.objects.get(username='testclient')
        data = {
            'username': 'testclient',
            'password': 'testclient',
            'date_of_birth': '1998-02-24',
        }
        form = CustomUserChangeForm(data, instance=user)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(form.cleaned_data['username'], 'testclient')
        self.assertEqual(form.cleaned_data['date_of_birth'], datetime.date(1998, 2, 24))


@override_settings(TEMPLATES=AUTH_TEMPLATES)
class PasswordResetFormTest(TestDataMixin, TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # This cleanup is necessary because contrib.sites cache
        # makes tests interfere with each other, see #11505
        Site.objects.clear_cache()

    def create_dummy_user(self):
        """
        Create a user and return a tuple (user_object, username, email).
        """
        username = 'jsmith'
        email = 'jsmith@example.com'
        user = User.objects.create_user(username, email, 'test123')
        return (user, username, email)

    def test_invalid_email(self):
        data = {'email': 'not valid'}
        form = PasswordResetForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form['email'].errors, [_('Enter a valid email address.')])

    def test_nonexistent_email(self):
        """
        Test nonexistent email address. This should not fail because it would
        expose information about registered users.
        """
        data = {'email': 'foo@bar.com'}
        form = PasswordResetForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(mail.outbox), 0)

    def test_cleaned_data(self):
        (user, username, email) = self.create_dummy_user()
        data = {'email': email}
        form = PasswordResetForm(data)
        self.assertTrue(form.is_valid())
        form.save(domain_override='example.com')
        self.assertEqual(form.cleaned_data['email'], email)
        self.assertEqual(len(mail.outbox), 1)

    def test_custom_email_subject(self):
        data = {'email': 'testclient@example.com'}
        form = PasswordResetForm(data)
        self.assertTrue(form.is_valid())
        # Since we're not providing a request object, we must provide a
        # domain_override to prevent the save operation from failing in the
        # potential case where contrib.sites is not installed. Refs #16412.
        form.save(domain_override='example.com')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Custom password reset on example.com')

    def test_custom_email_constructor(self):
        data = {'email': 'testclient@example.com'}

        class CustomEmailPasswordResetForm(PasswordResetForm):
            def send_mail(self, subject_template_name, email_template_name,
                          context, from_email, to_email,
                          html_email_template_name=None):
                EmailMultiAlternatives(
                    "Forgot your password?",
                    "Sorry to hear you forgot your password.",
                    None, [to_email],
                    ['site_monitor@example.com'],
                    headers={'Reply-To': 'webmaster@example.com'},
                    alternatives=[
                        ("Really sorry to hear you forgot your password.", "text/html")
                    ],
                ).send()

        form = CustomEmailPasswordResetForm(data)
        self.assertTrue(form.is_valid())
        # Since we're not providing a request object, we must provide a
        # domain_override to prevent the save operation from failing in the
        # potential case where contrib.sites is not installed. Refs #16412.
        form.save(domain_override='example.com')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Forgot your password?')
        self.assertEqual(mail.outbox[0].bcc, ['site_monitor@example.com'])
        self.assertEqual(mail.outbox[0].content_subtype, "plain")

    def test_preserve_username_case(self):
        """
        Preserve the case of the user name (before the @ in the email address)
        when creating a user (#5605).
        """
        user = User.objects.create_user('forms_test2', 'tesT@EXAMple.com', 'test')
        self.assertEqual(user.email, 'tesT@example.com')
        user = User.objects.create_user('forms_test3', 'tesT', 'test')
        self.assertEqual(user.email, 'tesT')

    def test_inactive_user(self):
        """
        Inactive user cannot receive password reset email.
        """
        (user, username, email) = self.create_dummy_user()
        user.is_active = False
        user.save()
        form = PasswordResetForm({'email': email})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(len(mail.outbox), 0)

    def test_unusable_password(self):
        user = User.objects.create_user('testuser', 'test@example.com', 'test')
        data = {"email": "test@example.com"}
        form = PasswordResetForm(data)
        self.assertTrue(form.is_valid())
        user.set_unusable_password()
        user.save()
        form = PasswordResetForm(data)
        # The form itself is valid, but no email is sent
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(len(mail.outbox), 0)

    def test_save_plaintext_email(self):
        """
        Test the PasswordResetForm.save() method with no html_email_template_name
        parameter passed in.
        Test to ensure original behavior is unchanged after the parameter was added.
        """
        (user, username, email) = self.create_dummy_user()
        form = PasswordResetForm({"email": email})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0].message()
        self.assertFalse(message.is_multipart())
        self.assertEqual(message.get_content_type(), 'text/plain')
        self.assertEqual(message.get('subject'), 'Custom password reset on example.com')
        self.assertEqual(len(mail.outbox[0].alternatives), 0)
        self.assertEqual(message.get_all('to'), [email])
        self.assertTrue(re.match(r'^http://example.com/reset/[\w+/-]', message.get_payload()))

    def test_save_html_email_template_name(self):
        """
        Test the PasswordResetFOrm.save() method with html_email_template_name
        parameter specified.
        Test to ensure that a multipart email is sent with both text/plain
        and text/html parts.
        """
        (user, username, email) = self.create_dummy_user()
        form = PasswordResetForm({"email": email})
        self.assertTrue(form.is_valid())
        form.save(html_email_template_name='registration/html_password_reset_email.html')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        message = mail.outbox[0].message()
        self.assertEqual(message.get('subject'), 'Custom password reset on example.com')
        self.assertEqual(len(message.get_payload()), 2)
        self.assertTrue(message.is_multipart())
        self.assertEqual(message.get_payload(0).get_content_type(), 'text/plain')
        self.assertEqual(message.get_payload(1).get_content_type(), 'text/html')
        self.assertEqual(message.get_all('to'), [email])
        self.assertTrue(re.match(r'^http://example.com/reset/[\w/-]+', message.get_payload(0).get_payload()))
        self.assertTrue(re.match(
            r'^<html><a href="http://example.com/reset/[\w/-]+/">Link</a></html>$',
            message.get_payload(1).get_payload()
        ))

    @override_settings(AUTH_USER_MODEL='auth_tests.CustomEmailField')
    def test_custom_email_field(self):
        email = 'test@mail.com'
        CustomEmailField.objects.create_user('test name', 'test password', email)
        form = PasswordResetForm({'email': email})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(form.cleaned_data['email'], email)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [email])


class ReadOnlyPasswordHashTest(SimpleTestCase):

    def test_bug_19349_render_with_none_value(self):
        # Rendering the widget with value set to None
        # mustn't raise an exception.
        widget = ReadOnlyPasswordHashWidget()
        html = widget.render(name='password', value=None, attrs={})
        self.assertIn(_("No password set."), html)

    @override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.PBKDF2PasswordHasher'])
    def test_render(self):
        widget = ReadOnlyPasswordHashWidget()
        value = 'pbkdf2_sha256$100000$a6Pucb1qSFcD$WmCkn9Hqidj48NVe5x0FEM6A9YiOqQcl/83m2Z5udm0='
        self.assertHTMLEqual(
            widget.render('name', value, {'id': 'id_password'}),
            """
            <div id="id_password">
                <strong>algorithm</strong>: pbkdf2_sha256
                <strong>iterations</strong>: 100000
                <strong>salt</strong>: a6Pucb******
                <strong>hash</strong>: WmCkn9**************************************
            </div>
            """
        )

    def test_readonly_field_has_changed(self):
        field = ReadOnlyPasswordHashField()
        self.assertFalse(field.has_changed('aaa', 'bbb'))


class AdminPasswordChangeFormTest(TestDataMixin, TestCase):

    @mock.patch('django.contrib.auth.password_validation.password_changed')
    def test_success(self, password_changed):
        user = User.objects.get(username='testclient')
        data = {
            'password1': 'test123',
            'password2': 'test123',
        }
        form = AdminPasswordChangeForm(user, data)
        self.assertTrue(form.is_valid())
        form.save(commit=False)
        self.assertEqual(password_changed.call_count, 0)
        form.save()
        self.assertEqual(password_changed.call_count, 1)

    def test_password_whitespace_not_stripped(self):
        user = User.objects.get(username='testclient')
        data = {
            'password1': ' pass ',
            'password2': ' pass ',
        }
        form = AdminPasswordChangeForm(user, data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['password1'], data['password1'])
        self.assertEqual(form.cleaned_data['password2'], data['password2'])
