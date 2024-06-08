from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.middleware import (
    AuthenticationMiddleware,
    LoginRequiredMiddleware,
)
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse
from django.test import TestCase, modify_settings, override_settings
from django.urls import reverse


class TestAuthenticationMiddleware(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            "test_user", "test@example.com", "test_password"
        )

    def setUp(self):
        self.middleware = AuthenticationMiddleware(lambda req: HttpResponse())
        self.client.force_login(self.user)
        self.request = HttpRequest()
        self.request.session = self.client.session

    def test_no_password_change_doesnt_invalidate_session(self):
        self.request.session = self.client.session
        self.middleware(self.request)
        self.assertIsNotNone(self.request.user)
        self.assertFalse(self.request.user.is_anonymous)

    def test_changed_password_invalidates_session(self):
        # After password change, user should be anonymous
        self.user.set_password("new_password")
        self.user.save()
        self.middleware(self.request)
        self.assertIsNotNone(self.request.user)
        self.assertTrue(self.request.user.is_anonymous)
        # session should be flushed
        self.assertIsNone(self.request.session.session_key)

    def test_no_session(self):
        msg = (
            "The Django authentication middleware requires session middleware "
            "to be installed. Edit your MIDDLEWARE setting to insert "
            "'django.contrib.sessions.middleware.SessionMiddleware' before "
            "'django.contrib.auth.middleware.AuthenticationMiddleware'."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            self.middleware(HttpRequest())

    async def test_auser(self):
        self.middleware(self.request)
        auser = await self.request.auser()
        self.assertEqual(auser, self.user)
        auser_second = await self.request.auser()
        self.assertIs(auser, auser_second)


@override_settings(ROOT_URLCONF="auth_tests.urls")
@modify_settings(
    MIDDLEWARE={"append": "django.contrib.auth.middleware.LoginRequiredMiddleware"}
)
class TestLoginRequiredMiddleware(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            "test_user", "test@example.com", "test_password"
        )

    def setUp(self):
        self.middleware = LoginRequiredMiddleware(lambda req: HttpResponse())
        self.request = HttpRequest()

    def test_public_paths(self):
        paths = ["public_view", "public_function_view"]
        for path in paths:
            response = self.client.get(f"/{path}/")
            self.assertEqual(response.status_code, 200)

    def test_protected_paths(self):
        paths = ["protected_view", "protected_function_view"]
        for path in paths:
            response = self.client.get(f"/{path}/")
            self.assertRedirects(
                response,
                settings.LOGIN_URL + f"?next=/{path}/",
                fetch_redirect_response=False,
            )

    def test_login_required_paths(self):
        paths = ["login_required_cbv_view", "login_required_decorator_view"]
        for path in paths:
            response = self.client.get(f"/{path}/")
            self.assertRedirects(
                response,
                "/custom_login/" + f"?step=/{path}/",
                fetch_redirect_response=False,
            )

    def test_admin_path(self):
        admin_url = reverse("admin:index")
        response = self.client.get(admin_url)
        self.assertRedirects(
            response,
            reverse("admin:login") + f"?next={admin_url}",
            target_status_code=200,
        )

    def test_non_existent_path(self):
        response = self.client.get("/non_existent/")
        self.assertEqual(response.status_code, 404)

    def test_paths_with_logged_in_user(self):
        paths = [
            "public_view",
            "public_function_view",
            "protected_view",
            "protected_function_view",
            "login_required_cbv_view",
            "login_required_decorator_view",
        ]
        self.client.login(username="test_user", password="test_password")
        for path in paths:
            response = self.client.get(f"/{path}/")
            self.assertEqual(response.status_code, 200)

    def test_get_login_url_from_view_func(self):
        def view_func(request):
            return HttpResponse()

        view_func.login_url = "/custom_login/"
        login_url = self.middleware.get_login_url(view_func)
        self.assertEqual(login_url, "/custom_login/")

    @override_settings(LOGIN_URL="/settings_login/")
    def test_get_login_url_from_settings(self):
        login_url = self.middleware.get_login_url(lambda: None)
        self.assertEqual(login_url, "/settings_login/")

    @override_settings(LOGIN_URL=None)
    def test_get_login_url_no_login_url(self):
        with self.assertRaises(ImproperlyConfigured) as e:
            self.middleware.get_login_url(lambda: None)
        self.assertEqual(
            str(e.exception),
            "No login URL to redirect to. Define settings.LOGIN_URL or provide "
            "a login_url via the 'django.contrib.auth.decorators.login_required' "
            "decorator.",
        )

    def test_get_redirect_field_name_from_view_func(self):
        def view_func(request):
            return HttpResponse()

        view_func.redirect_field_name = "next_page"
        redirect_field_name = self.middleware.get_redirect_field_name(view_func)
        self.assertEqual(redirect_field_name, "next_page")

    @override_settings(
        MIDDLEWARE=[
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "auth_tests.test_checks.LoginRequiredMiddlewareSubclass",
        ],
        LOGIN_URL="/settings_login/",
    )
    def test_login_url_resolve_logic(self):
        paths = ["login_required_cbv_view", "login_required_decorator_view"]
        for path in paths:
            response = self.client.get(f"/{path}/")
            self.assertRedirects(
                response,
                "/custom_login/" + f"?step=/{path}/",
                fetch_redirect_response=False,
            )
        paths = ["protected_view", "protected_function_view"]
        for path in paths:
            response = self.client.get(f"/{path}/")
            self.assertRedirects(
                response,
                f"/settings_login/?redirect_to=/{path}/",
                fetch_redirect_response=False,
            )

    def test_get_redirect_field_name_default(self):
        redirect_field_name = self.middleware.get_redirect_field_name(lambda: None)
        self.assertEqual(redirect_field_name, REDIRECT_FIELD_NAME)
