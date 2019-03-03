from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.views import (
    PasswordChangeDoneView, PasswordChangeView, PasswordResetCompleteView,
    PasswordResetDoneView, PasswordResetView,
)
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode

from .client import PasswordResetConfirmClient


@override_settings(ROOT_URLCONF='auth_tests.urls')
class AuthTemplateTests(TestCase):
    request_factory = RequestFactory()

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user('jsmith', 'jsmith@example.com', 'pass')
        user = authenticate(username=user.username, password='pass')
        request = cls.request_factory.get('/somepath/')
        request.user = user
        cls.user, cls.request = user, request

    def test_PasswordResetView(self):
        response = PasswordResetView.as_view(success_url='dummy/')(self.request)
        self.assertContains(response, '<title>Password reset</title>')
        self.assertContains(response, '<h1>Password reset</h1>')

    def test_PasswordResetDoneView(self):
        response = PasswordResetDoneView.as_view()(self.request)
        self.assertContains(response, '<title>Password reset sent</title>')
        self.assertContains(response, '<h1>Password reset sent</h1>')

    def test_PasswordResetConfirmView_invalid_token(self):
        # PasswordResetConfirmView invalid token
        client = PasswordResetConfirmClient()
        url = reverse('password_reset_confirm', kwargs={'uidb64': 'Bad', 'token': 'Bad-Token'})
        response = client.get(url)
        self.assertContains(response, '<title>Password reset unsuccessful</title>')
        self.assertContains(response, '<h1>Password reset unsuccessful</h1>')

    def test_PasswordResetConfirmView_valid_token(self):
        # PasswordResetConfirmView valid token
        client = PasswordResetConfirmClient()
        default_token_generator = PasswordResetTokenGenerator()
        token = default_token_generator.make_token(self.user)
        uidb64 = urlsafe_base64_encode(str(self.user.pk).encode())
        url = reverse('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})
        response = client.get(url)
        self.assertContains(response, '<title>Enter new password</title>')
        self.assertContains(response, '<h1>Enter new password</h1>')

    def test_PasswordResetCompleteView(self):
        response = PasswordResetCompleteView.as_view()(self.request)
        self.assertContains(response, '<title>Password reset complete</title>')
        self.assertContains(response, '<h1>Password reset complete</h1>')

    def test_PasswordResetChangeView(self):
        response = PasswordChangeView.as_view(success_url='dummy/')(self.request)
        self.assertContains(response, '<title>Password change</title>')
        self.assertContains(response, '<h1>Password change</h1>')

    def test_PasswordChangeDoneView(self):
        response = PasswordChangeDoneView.as_view()(self.request)
        self.assertContains(response, '<title>Password change successful</title>')
        self.assertContains(response, '<h1>Password change successful</h1>')
