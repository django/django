from __future__ import unicode_literals

import os
import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.forms import (UserCreationForm, AuthenticationForm,
    PasswordChangeForm, SetPasswordForm, UserChangeForm, PasswordResetForm,
    ReadOnlyPasswordHashField, ReadOnlyPasswordHashWidget)
from django.contrib.auth.tests.utils import skipIfCustomUser
from django.core import mail
from django.forms.fields import Field, CharField
from django.test import TestCase, override_settings
from django.utils.encoding import force_text
from django.utils._os import upath
from django.utils import translation
from django.utils.text import capfirst
from django.utils.translation import ugettext as _


@skipIfCustomUser
@override_settings(USE_TZ=False, PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class UserCreationFormTest(TestCase):

    fixtures = ['authtestdata.json']

    def test_user_already_exists(self):
        data = {
            'username': 'testclient',
            'password1': 'test123',
            'password2': 'test123',
        }
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["username"].errors,
                         [force_text(form.error_messages['duplicate_username'])])

    def test_invalid_data(self):
        data = {
            'username': 'jsmith!',
            'password1': 'test123',
            'password2': 'test123',
        }
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["username"].errors,
                         [force_text(form.fields['username'].error_messages['invalid'])])

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
                         [force_text(form.error_messages['password_mismatch'])])

    def test_both_passwords(self):
        # One (or both) passwords weren't given
        data = {'username': 'jsmith'}
        form = UserCreationForm(data)
        required_error = [force_text(Field.default_error_messages['required'])]
        self.assertFalse(form.is_valid())
        self.assertEqual(form['password1'].errors, required_error)
        self.assertEqual(form['password2'].errors, required_error)

        data['password2'] = 'test123'
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form['password1'].errors, required_error)
        self.assertEqual(form['password2'].errors, [])

    def test_success(self):
        # The success case.
        data = {
            'username': 'jsmith@example.com',
            'password1': 'test123',
            'password2': 'test123',
        }
        form = UserCreationForm(data)
        self.assertTrue(form.is_valid())
        u = form.save()
        self.assertEqual(repr(u), '<User: jsmith@example.com>')


@skipIfCustomUser
@override_settings(USE_TZ=False, PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class AuthenticationFormTest(TestCase):

    fixtures = ['authtestdata.json']

    def test_invalid_username(self):
        # The user submits an invalid username.

        data = {
            'username': 'jsmith_does_not_exist',
            'password': 'test123',
        }
        form = AuthenticationForm(None, data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(),
                [force_text(form.error_messages['invalid_login'] % {
                    'username': User._meta.get_field('username').verbose_name
                })])

    def test_inactive_user(self):
        # The user is inactive.
        data = {
            'username': 'inactive',
            'password': 'password',
        }
        form = AuthenticationForm(None, data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(),
                         [force_text(form.error_messages['inactive'])])

    def test_inactive_user_i18n(self):
        with self.settings(USE_I18N=True), translation.override('pt-br', deactivate=True):
            # The user is inactive.
            data = {
                'username': 'inactive',
                'password': 'password',
            }
            form = AuthenticationForm(None, data)
            self.assertFalse(form.is_valid())
            self.assertEqual(form.non_field_errors(),
                             [force_text(form.error_messages['inactive'])])

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

    def test_username_field_label(self):

        class CustomAuthenticationForm(AuthenticationForm):
            username = CharField(label="Name", max_length=75)

        form = CustomAuthenticationForm()
        self.assertEqual(form['username'].label, "Name")

    def test_username_field_label_not_set(self):

        class CustomAuthenticationForm(AuthenticationForm):
            username = CharField()

        form = CustomAuthenticationForm()
        UserModel = get_user_model()
        username_field = UserModel._meta.get_field(UserModel.USERNAME_FIELD)
        self.assertEqual(form.fields['username'].label, capfirst(username_field.verbose_name))

    def test_username_field_label_empty_string(self):

        class CustomAuthenticationForm(AuthenticationForm):
            username = CharField(label='')

        form = CustomAuthenticationForm()
        self.assertEqual(form.fields['username'].label, "")


@skipIfCustomUser
@override_settings(USE_TZ=False, PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class SetPasswordFormTest(TestCase):

    fixtures = ['authtestdata.json']

    def test_password_verification(self):
        # The two new passwords do not match.
        user = User.objects.get(username='testclient')
        data = {
            'new_password1': 'abc123',
            'new_password2': 'abc',
        }
        form = SetPasswordForm(user, data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["new_password2"].errors,
                         [force_text(form.error_messages['password_mismatch'])])

    def test_success(self):
        user = User.objects.get(username='testclient')
        data = {
            'new_password1': 'abc123',
            'new_password2': 'abc123',
        }
        form = SetPasswordForm(user, data)
        self.assertTrue(form.is_valid())


@skipIfCustomUser
@override_settings(USE_TZ=False, PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class PasswordChangeFormTest(TestCase):

    fixtures = ['authtestdata.json']

    def test_incorrect_password(self):
        user = User.objects.get(username='testclient')
        data = {
            'old_password': 'test',
            'new_password1': 'abc123',
            'new_password2': 'abc123',
        }
        form = PasswordChangeForm(user, data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["old_password"].errors,
                         [force_text(form.error_messages['password_incorrect'])])

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
        self.assertEqual(form["new_password2"].errors,
                         [force_text(form.error_messages['password_mismatch'])])

    def test_success(self):
        # The success case.
        user = User.objects.get(username='testclient')
        data = {
            'old_password': 'password',
            'new_password1': 'abc123',
            'new_password2': 'abc123',
        }
        form = PasswordChangeForm(user, data)
        self.assertTrue(form.is_valid())

    def test_field_order(self):
        # Regression test - check the order of fields:
        user = User.objects.get(username='testclient')
        self.assertEqual(list(PasswordChangeForm(user, {}).fields),
                         ['old_password', 'new_password1', 'new_password2'])


@skipIfCustomUser
@override_settings(USE_TZ=False, PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class UserChangeFormTest(TestCase):

    fixtures = ['authtestdata.json']

    def test_username_validity(self):
        user = User.objects.get(username='testclient')
        data = {'username': 'not valid'}
        form = UserChangeForm(data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertEqual(form['username'].errors,
                         [force_text(form.fields['username'].error_messages['invalid'])])

    def test_bug_14242(self):
        # A regression test, introduce by adding an optimization for the
        # UserChangeForm.

        class MyUserForm(UserChangeForm):
            def __init__(self, *args, **kwargs):
                super(MyUserForm, self).__init__(*args, **kwargs)
                self.fields['groups'].help_text = 'These groups give users different permissions'

            class Meta(UserChangeForm.Meta):
                fields = ('groups',)

        # Just check we can create it
        MyUserForm({})

    def test_unsuable_password(self):
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
        self.assertIn(_("Invalid password format or unknown hashing algorithm."),
            form.as_table())

    def test_bug_17944_unknown_password_algorithm(self):
        user = User.objects.get(username='unknown_password')
        form = UserChangeForm(instance=user)
        self.assertIn(_("Invalid password format or unknown hashing algorithm."),
            form.as_table())

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
        self.assertEqual(form.cleaned_data['password'], 'sha1$6efc0$f93efe9fd7542f25a7be94871ea45aa95de57161')

    def test_bug_19349_bound_password_field(self):
        user = User.objects.get(username='testclient')
        form = UserChangeForm(data={}, instance=user)
        # When rendering the bound password field,
        # ReadOnlyPasswordHashWidget needs the initial
        # value to render correctly
        self.assertEqual(form.initial['password'], form['password'].value())


@skipIfCustomUser
@override_settings(
    PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',),
    TEMPLATE_LOADERS=('django.template.loaders.filesystem.Loader',),
    TEMPLATE_DIRS=(
        os.path.join(os.path.dirname(upath(__file__)), 'templates'),
    ),
    USE_TZ=False,
)
class PasswordResetFormTest(TestCase):

    fixtures = ['authtestdata.json']

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
        Test that inactive user cannot receive password reset email.
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
        self.assertTrue(re.match(r'^<html><a href="http://example.com/reset/[\w/-]+/">Link</a></html>$', message.get_payload(1).get_payload()))


class ReadOnlyPasswordHashTest(TestCase):

    def test_bug_19349_render_with_none_value(self):
        # Rendering the widget with value set to None
        # mustn't raise an exception.
        widget = ReadOnlyPasswordHashWidget()
        html = widget.render(name='password', value=None, attrs={})
        self.assertIn(_("No password set."), html)

    def test_readonly_field_has_changed(self):
        field = ReadOnlyPasswordHashField()
        self.assertFalse(field._has_changed('aaa', 'bbb'))
