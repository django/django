from django.contrib.auth.tests.auth_backends import (BackendTest,
    RowlevelBackendTest, AnonymousUserBackendTest, NoBackendsTest,
    InActiveUserBackendTest, NoInActiveUserBackendTest)
from django.contrib.auth.tests.basic import BasicTestCase, PasswordUtilsTestCase
from django.contrib.auth.tests.context_processors import AuthContextProcessorTests
from django.contrib.auth.tests.decorators import LoginRequiredTestCase
from django.contrib.auth.tests.forms import (UserCreationFormTest,
    AuthenticationFormTest, SetPasswordFormTest, PasswordChangeFormTest,
    UserChangeFormTest, PasswordResetFormTest)
from django.contrib.auth.tests.remote_user import (RemoteUserTest,
    RemoteUserNoCreateTest, RemoteUserCustomTest)
from django.contrib.auth.tests.management import GetDefaultUsernameTestCase
from django.contrib.auth.tests.models import ProfileTestCase
from django.contrib.auth.tests.signals import SignalTestCase
from django.contrib.auth.tests.tokens import TokenGeneratorTest
from django.contrib.auth.tests.views import (AuthViewNamedURLTests, PasswordResetTest,
    ChangePasswordTest, LoginTest, LogoutTest, LoginURLSettings)

# The password for the fixture data users is 'password'
