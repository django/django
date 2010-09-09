from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm,  PasswordChangeForm, SetPasswordForm, UserChangeForm, PasswordResetForm
from django.test import TestCase


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
                         [u'A user with that username already exists.'])

    def test_invalid_data(self):
        data = {
            'username': 'jsmith!',
            'password1': 'test123',
            'password2': 'test123',
            }
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form["username"].errors,
                         [u'This value may contain only letters, numbers and @/./+/-/_ characters.'])


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
                         [u"The two password fields didn't match."])


    def test_both_passwords(self):
        # One (or both) passwords weren't given
        data = {'username': 'jsmith'}
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form['password1'].errors,
                         [u'This field is required.'])
        self.assertEqual(form['password2'].errors,
                         [u'This field is required.'])


        data['password2'] = 'test123'
        form = UserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form['password1'].errors,
                         [u'This field is required.'])

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
                         [u'Please enter a correct username and password. Note that both fields are case-sensitive.'])

    def test_inactive_user(self):
        # The user is inactive.
        data = {
            'username': 'inactive',
            'password': 'password',
            }
        form = AuthenticationForm(None, data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(),
                         [u'This account is inactive.'])


    def test_success(self):
        # The success case
        data = {
            'username': 'testclient',
            'password': 'password',
            }
        form = AuthenticationForm(None, data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.non_field_errors(), [])


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
                         [u"The two password fields didn't match."])

    def test_success(self):
        user = User.objects.get(username='testclient')
        data = {
            'new_password1': 'abc123',
            'new_password2': 'abc123',
            }
        form = SetPasswordForm(user, data)
        self.assertTrue(form.is_valid())


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
                         [u'Your old password was entered incorrectly. Please enter it again.'])


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
                         [u"The two password fields didn't match."])


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
        self.assertEqual(PasswordChangeForm(user, {}).fields.keys(),
                         ['old_password', 'new_password1', 'new_password2'])

class UserChangeFormTest(TestCase):

    fixtures = ['authtestdata.json']

    def test_username_validity(self):
        user = User.objects.get(username='testclient')
        data = {'username': 'not valid'}
        form = UserChangeForm(data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertEqual(form['username'].errors,
                         [u'This value may contain only letters, numbers and @/./+/-/_ characters.'])

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
        form = MyUserForm({})


class PasswordResetFormTest(TestCase):

    fixtures = ['authtestdata.json']

    def test_invalid_email(self):
        data = {'email':'not valid'}
        form = PasswordResetForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form['email'].errors,
                         [u'Enter a valid e-mail address.'])

    def test_nonexistant_email(self):
        # Test nonexistant email address
        data = {'email':'foo@bar.com'}
        form = PasswordResetForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors,
                         {'email': [u"That e-mail address doesn't have an associated user account. Are you sure you've registered?"]})

    def test_cleaned_data(self):
        # Regression test
        user = User.objects.create_user("jsmith3", "jsmith3@example.com", "test123")
        data = {'email':'jsmith3@example.com'}
        form = PasswordResetForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['email'], u'jsmith3@example.com')


    def test_bug_5605(self):
        # bug #5605, preserve the case of the user name (before the @ in the
        # email address) when creating a user.
        user = User.objects.create_user('forms_test2', 'tesT@EXAMple.com', 'test')
        self.assertEqual(user.email, 'tesT@example.com')
        user = User.objects.create_user('forms_test3', 'tesT', 'test')
        self.assertEqual(user.email, 'tesT')
