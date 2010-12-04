from django.contrib.auth.tests.auth_backends import BackendTest, RowlevelBackendTest, AnonymousUserBackendTest, NoAnonymousUserBackendTest, NoBackendsTest
from django.contrib.auth.tests.basic import BasicTestCase
from django.contrib.auth.tests.decorators import LoginRequiredTestCase
from django.contrib.auth.tests.forms import UserCreationFormTest, AuthenticationFormTest, SetPasswordFormTest, PasswordChangeFormTest, UserChangeFormTest, PasswordResetFormTest
from django.contrib.auth.tests.remote_user \
        import RemoteUserTest, RemoteUserNoCreateTest, RemoteUserCustomTest
from django.contrib.auth.tests.models import ProfileTestCase
from django.contrib.auth.tests.signals import SignalTestCase
from django.contrib.auth.tests.tokens import TokenGeneratorTest
from django.contrib.auth.tests.views import PasswordResetTest, \
    ChangePasswordTest, LoginTest, LogoutTest, LoginURLSettings

# The password for the fixture data users is 'password'
