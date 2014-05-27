from freedom.contrib.auth import authenticate
from freedom.contrib.auth.models import User
from freedom.contrib.auth.tests.utils import skipIfCustomUser
from freedom.contrib.auth.tokens import PasswordResetTokenGenerator
from freedom.contrib.auth.views import (
    password_reset, password_reset_done, password_reset_confirm,
    password_reset_complete, password_change, password_change_done,
)
from freedom.test import RequestFactory, TestCase
from freedom.test import override_settings
from freedom.utils.encoding import force_bytes, force_text
from freedom.utils.http import urlsafe_base64_encode


@skipIfCustomUser
@override_settings(
    PASSWORD_HASHERS=('freedom.contrib.auth.hashers.SHA1PasswordHasher',),
    ROOT_URLCONF='freedom.contrib.auth.tests.urls',
)
class AuthTemplateTests(TestCase):

    def test_titles(self):
        rf = RequestFactory()
        user = User.objects.create_user('jsmith', 'jsmith@example.com', 'pass')
        user = authenticate(username=user.username, password='pass')
        request = rf.get('/somepath/')
        request.user = user

        response = password_reset(request, post_reset_redirect='dummy/')
        self.assertContains(response, '<title>Password reset</title>')
        self.assertContains(response, '<h1>Password reset</h1>')

        response = password_reset_done(request)
        self.assertContains(response, '<title>Password reset successful</title>')
        self.assertContains(response, '<h1>Password reset successful</h1>')

        # password_reset_confirm invalid token
        response = password_reset_confirm(request, uidb64='Bad', token='Bad', post_reset_redirect='dummy/')
        self.assertContains(response, '<title>Password reset unsuccessful</title>')
        self.assertContains(response, '<h1>Password reset unsuccessful</h1>')

        # password_reset_confirm valid token
        default_token_generator = PasswordResetTokenGenerator()
        token = default_token_generator.make_token(user)
        uidb64 = force_text(urlsafe_base64_encode(force_bytes(user.pk)))
        response = password_reset_confirm(request, uidb64, token, post_reset_redirect='dummy/')
        self.assertContains(response, '<title>Enter new password</title>')
        self.assertContains(response, '<h1>Enter new password</h1>')

        response = password_reset_complete(request)
        self.assertContains(response, '<title>Password reset complete</title>')
        self.assertContains(response, '<h1>Password reset complete</h1>')

        response = password_change(request, post_change_redirect='dummy/')
        self.assertContains(response, '<title>Password change</title>')
        self.assertContains(response, '<h1>Password change</h1>')

        response = password_change_done(request)
        self.assertContains(response, '<title>Password change successful</title>')
        self.assertContains(response, '<h1>Password change successful</h1>')
