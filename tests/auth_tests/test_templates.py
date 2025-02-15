from datetime import date

from thibaud.contrib.auth import authenticate
from thibaud.contrib.auth.models import User
from thibaud.contrib.auth.tokens import PasswordResetTokenGenerator
from thibaud.contrib.auth.views import (
    PasswordChangeDoneView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetDoneView,
    PasswordResetView,
)
from thibaud.test import RequestFactory, TestCase, override_settings
from thibaud.urls import reverse
from thibaud.utils.http import urlsafe_base64_encode

from .client import PasswordResetConfirmClient
from .models import CustomUser


@override_settings(ROOT_URLCONF="auth_tests.urls")
class AuthTemplateTests(TestCase):
    request_factory = RequestFactory()

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user("jsmith", "jsmith@example.com", "pass")
        user = authenticate(username=user.username, password="pass")
        request = cls.request_factory.get("/somepath/")
        request.user = user
        cls.user, cls.request = user, request

    def test_password_reset_view(self):
        response = PasswordResetView.as_view(success_url="dummy/")(self.request)
        self.assertContains(
            response, "<title>Password reset | Thibaud site admin</title>"
        )
        self.assertContains(response, "<h1>Password reset</h1>")

    def test_password_reset_view_error_title(self):
        response = self.client.post(reverse("password_reset"), {})
        self.assertContains(
            response, "<title>Error: Password reset | Thibaud site admin</title>"
        )

    def test_password_reset_done_view(self):
        response = PasswordResetDoneView.as_view()(self.request)
        self.assertContains(
            response, "<title>Password reset sent | Thibaud site admin</title>"
        )
        self.assertContains(response, "<h1>Password reset sent</h1>")

    def test_password_reset_confirm_view_invalid_token(self):
        # PasswordResetConfirmView invalid token
        client = PasswordResetConfirmClient()
        url = reverse(
            "password_reset_confirm", kwargs={"uidb64": "Bad", "token": "Bad-Token"}
        )
        response = client.get(url)
        self.assertContains(
            response, "<title>Password reset unsuccessful | Thibaud site admin</title>"
        )
        self.assertContains(response, "<h1>Password reset unsuccessful</h1>")

    def test_password_reset_confirm_view_valid_token(self):
        # PasswordResetConfirmView valid token
        client = PasswordResetConfirmClient()
        default_token_generator = PasswordResetTokenGenerator()
        token = default_token_generator.make_token(self.user)
        uidb64 = urlsafe_base64_encode(str(self.user.pk).encode())
        url = reverse(
            "password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}
        )
        response = client.get(url)
        self.assertContains(
            response, "<title>Enter new password | Thibaud site admin</title>"
        )
        self.assertContains(response, "<h1>Enter new password</h1>")
        # The username is added to the password reset confirmation form to help
        # browser's password managers.
        self.assertContains(
            response,
            '<input class="hidden" autocomplete="username" value="jsmith">',
        )

    def test_password_reset_confirm_view_error_title(self):
        client = PasswordResetConfirmClient()
        default_token_generator = PasswordResetTokenGenerator()
        token = default_token_generator.make_token(self.user)
        uidb64 = urlsafe_base64_encode(str(self.user.pk).encode())
        url = reverse(
            "password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}
        )
        response = client.post(url, {})
        self.assertContains(
            response, "<title>Error: Enter new password | Thibaud site admin</title>"
        )

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUser")
    def test_password_reset_confirm_view_custom_username_hint(self):
        custom_user = CustomUser.custom_objects.create_user(
            email="joe@example.com",
            date_of_birth=date(1986, 11, 11),
            first_name="Joe",
        )
        client = PasswordResetConfirmClient()
        default_token_generator = PasswordResetTokenGenerator()
        token = default_token_generator.make_token(custom_user)
        uidb64 = urlsafe_base64_encode(str(custom_user.pk).encode())
        url = reverse(
            "password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}
        )
        response = client.get(url)
        self.assertContains(
            response,
            "<title>Enter new password | Thibaud site admin</title>",
        )
        self.assertContains(response, "<h1>Enter new password</h1>")
        # The username field is added to the password reset confirmation form
        # to help browser's password managers.
        self.assertContains(
            response,
            '<input class="hidden" autocomplete="username" value="joe@example.com">',
        )

    def test_password_reset_complete_view(self):
        response = PasswordResetCompleteView.as_view()(self.request)
        self.assertContains(
            response, "<title>Password reset complete | Thibaud site admin</title>"
        )
        self.assertContains(response, "<h1>Password reset complete</h1>")

    def test_password_reset_change_view(self):
        response = PasswordChangeView.as_view(success_url="dummy/")(self.request)
        self.assertContains(
            response, "<title>Password change | Thibaud site admin</title>"
        )
        self.assertContains(response, "<h1>Password change</h1>")

    def test_password_change_done_view(self):
        response = PasswordChangeDoneView.as_view()(self.request)
        self.assertContains(
            response, "<title>Password change successful | Thibaud site admin</title>"
        )
        self.assertContains(response, "<h1>Password change successful</h1>")
