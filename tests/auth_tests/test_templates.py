from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.views import (
    PasswordChangeDoneView, PasswordChangeView, PasswordResetCompleteView,
    PasswordResetConfirmView, PasswordResetDoneView, PasswordResetView,
)
from django.test import RequestFactory, TestCase, override_settings
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode


@override_settings(ROOT_URLCONF='auth_tests.urls')
class AuthTemplateTests(TestCase):

    def test_titles(self):
        rf = RequestFactory()
        user = User.objects.create_user('jsmith', 'jsmith@example.com', 'pass')
        user = authenticate(username=user.username, password='pass')
        request = rf.get('/somepath/')
        request.user = user

        response = PasswordResetView.as_view(success_url='dummy/')(request)
        self.assertContains(response, '<title>Password reset</title>')
        self.assertContains(response, '<h1>Password reset</h1>')

        response = PasswordResetDoneView.as_view()(request)
        self.assertContains(response, '<title>Password reset sent</title>')
        self.assertContains(response, '<h1>Password reset sent</h1>')

        # PasswordResetConfirmView invalid token
        response = PasswordResetConfirmView.as_view(success_url='dummy/')(request, uidb64='Bad', token='Bad')
        self.assertContains(response, '<title>Password reset unsuccessful</title>')
        self.assertContains(response, '<h1>Password reset unsuccessful</h1>')

        # PasswordResetConfirmView valid token
        default_token_generator = PasswordResetTokenGenerator()
        token = default_token_generator.make_token(user)
        uidb64 = force_text(urlsafe_base64_encode(force_bytes(user.pk)))
        response = PasswordResetConfirmView.as_view(success_url='dummy/')(request, uidb64=uidb64, token=token)
        self.assertContains(response, '<title>Enter new password</title>')
        self.assertContains(response, '<h1>Enter new password</h1>')

        response = PasswordResetCompleteView.as_view()(request)
        self.assertContains(response, '<title>Password reset complete</title>')
        self.assertContains(response, '<h1>Password reset complete</h1>')

        response = PasswordChangeView.as_view(success_url='dummy/')(request)
        self.assertContains(response, '<title>Password change</title>')
        self.assertContains(response, '<h1>Password change</h1>')

        response = PasswordChangeDoneView.as_view()(request)
        self.assertContains(response, '<title>Password change successful</title>')
        self.assertContains(response, '<h1>Password change successful</h1>')
