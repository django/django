
FORM_TESTS = """
>>> from django.contrib.auth.models import User
>>> from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
>>> from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm

# The user already exists.

>>> user = User.objects.create_user("jsmith", "jsmith@example.com", "test123")
>>> data = {
...     'username': 'jsmith',
...     'password1': 'test123',
...     'password2': 'test123',
... }
>>> form = UserCreationForm(data)
>>> form.is_valid()
False
>>> form["username"].errors
[u'A user with that username already exists.']

# The username contains invalid data.

>>> data = {
...     'username': 'jsmith!',
...     'password1': 'test123',
...     'password2': 'test123',
... }
>>> form = UserCreationForm(data)
>>> form.is_valid()
False
>>> form["username"].errors
[u'This value may contain only letters, numbers and @/./+/-/_ characters.']

# The verification password is incorrect.

>>> data = {
...     'username': 'jsmith2',
...     'password1': 'test123',
...     'password2': 'test',
... }
>>> form = UserCreationForm(data)
>>> form.is_valid()
False
>>> form["password2"].errors
[u"The two password fields didn't match."]

# One (or both) passwords weren't given

>>> data = {'username': 'jsmith2'}
>>> form = UserCreationForm(data)
>>> form.is_valid()
False
>>> form['password1'].errors
[u'This field is required.']
>>> form['password2'].errors
[u'This field is required.']

>>> data['password2'] = 'test123'
>>> form = UserCreationForm(data)
>>> form.is_valid()
False
>>> form['password1'].errors
[u'This field is required.']

# The success case.

>>> data = {
...     'username': 'jsmith2@example.com',
...     'password1': 'test123',
...     'password2': 'test123',
... }
>>> form = UserCreationForm(data)
>>> form.is_valid()
True
>>> form.save()
<User: jsmith2@example.com>

# The user submits an invalid username.

>>> data = {
...     'username': 'jsmith_does_not_exist',
...     'password': 'test123',
... }

>>> form = AuthenticationForm(None, data)
>>> form.is_valid()
False
>>> form.non_field_errors()
[u'Please enter a correct username and password. Note that both fields are case-sensitive.']

# The user is inactive.

>>> data = {
...     'username': 'jsmith',
...     'password': 'test123',
... }
>>> user.is_active = False
>>> user.save()
>>> form = AuthenticationForm(None, data)
>>> form.is_valid()
False
>>> form.non_field_errors()
[u'This account is inactive.']

>>> user.is_active = True
>>> user.save()

# The success case

>>> form = AuthenticationForm(None, data)
>>> form.is_valid()
True
>>> form.non_field_errors()
[]

### SetPasswordForm:

# The two new passwords do not match.

>>> data = {
...     'new_password1': 'abc123',
...     'new_password2': 'abc',
... }
>>> form = SetPasswordForm(user, data)
>>> form.is_valid()
False
>>> form["new_password2"].errors
[u"The two password fields didn't match."]

# The success case.

>>> data = {
...     'new_password1': 'abc123',
...     'new_password2': 'abc123',
... }
>>> form = SetPasswordForm(user, data)
>>> form.is_valid()
True

### PasswordChangeForm:

The old password is incorrect.

>>> data = {
...     'old_password': 'test',
...     'new_password1': 'abc123',
...     'new_password2': 'abc123',
... }
>>> form = PasswordChangeForm(user, data)
>>> form.is_valid()
False
>>> form["old_password"].errors
[u'Your old password was entered incorrectly. Please enter it again.']

# The two new passwords do not match.

>>> data = {
...     'old_password': 'test123',
...     'new_password1': 'abc123',
...     'new_password2': 'abc',
... }
>>> form = PasswordChangeForm(user, data)
>>> form.is_valid()
False
>>> form["new_password2"].errors
[u"The two password fields didn't match."]

# The success case.

>>> data = {
...     'old_password': 'test123',
...     'new_password1': 'abc123',
...     'new_password2': 'abc123',
... }
>>> form = PasswordChangeForm(user, data)
>>> form.is_valid()
True

# Regression test - check the order of fields:

>>> PasswordChangeForm(user, {}).fields.keys()
['old_password', 'new_password1', 'new_password2']

### UserChangeForm

>>> from django.contrib.auth.forms import UserChangeForm
>>> data = {'username': 'not valid'}
>>> form = UserChangeForm(data, instance=user)
>>> form.is_valid()
False
>>> form['username'].errors
[u'This value may contain only letters, numbers and @/./+/-/_ characters.']


### PasswordResetForm

>>> from django.contrib.auth.forms import PasswordResetForm
>>> data = {'email':'not valid'}
>>> form = PasswordResetForm(data)
>>> form.is_valid()
False
>>> form['email'].errors
[u'Enter a valid e-mail address.']

# Test nonexistant email address
>>> data = {'email':'foo@bar.com'}
>>> form = PasswordResetForm(data)
>>> form.is_valid()
False
>>> form.errors
{'email': [u"That e-mail address doesn't have an associated user account. Are you sure you've registered?"]}

# Test cleaned_data bug fix
>>> user = User.objects.create_user("jsmith3", "jsmith3@example.com", "test123")
>>> data = {'email':'jsmith3@example.com'}
>>> form = PasswordResetForm(data)
>>> form.is_valid()
True
>>> form.cleaned_data['email']
u'jsmith3@example.com'

# bug #5605, preserve the case of the user name (before the @ in the email address)
# when creating a user.
>>> user = User.objects.create_user('forms_test2', 'tesT@EXAMple.com', 'test')
>>> user.email
'tesT@example.com'
>>> user = User.objects.create_user('forms_test3', 'tesT', 'test')
>>> user.email
'tesT'

"""
