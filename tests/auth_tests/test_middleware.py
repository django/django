from django.contrib.auth import HASH_SESSION_KEY
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.middleware import (
    AuthenticationMiddleware, LoginRequiredAuthenticationMiddleware,
)
from django.contrib.auth.mixins import LoginNotRequiredMixin
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.http import HttpRequest, HttpResponse
from django.test import TestCase
from django.views import View


class TestAuthenticationMiddleware(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('test_user', 'test@example.com', 'test_password')

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

    def test_no_password_change_does_not_invalidate_legacy_session(self):
        # RemovedInDjango40Warning: pre-Django 3.1 hashes will be invalid.
        session = self.client.session
        session[HASH_SESSION_KEY] = self.user._legacy_get_session_auth_hash()
        session.save()
        self.request.session = session
        self.middleware(self.request)
        self.assertIsNotNone(self.request.user)
        self.assertFalse(self.request.user.is_anonymous)

    def test_changed_password_invalidates_session(self):
        # After password change, user should be anonymous
        self.user.set_password('new_password')
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
        with self.assertRaisesMessage(AssertionError, msg):
            self.middleware(HttpRequest())


class TestLoginRequiredAuthenticationMiddleware(TestCase):

    class EmptyResponseBaseView(View):
        def get(self, request, *args, **kwargs):
            return HttpResponse()

    class AView(EmptyResponseBaseView, LoginNotRequiredMixin):
        pass

    class BView(EmptyResponseBaseView):
        pass

    @login_not_required
    def func_viewA(self, request):
        return HttpResponse()

    def func_viewB(self, request):
        return HttpResponse()

    def setUp(self):
        self.user = User.objects.create_user('test_user', 'test@example.com', 'test_password')
        self.middleware = LoginRequiredAuthenticationMiddleware(lambda req: HttpResponse())
        self.request = HttpRequest()

    def test_anonymous_access(self):
        self.request.user = AnonymousUser()

        # LoginView is built-in view. It has LoginNotRequiredMixin.
        res = self.middleware.process_view(self.request, LoginView.as_view(), (), {})
        self.assertIsNone(res)

        # Aview has a LoginNotRequiredMixin mixin.
        res = self.middleware.process_view(self.request, self.AView.as_view(), (), {})
        self.assertIsNone(res)

        # func_viewA has a login_not_required annotation.
        res = self.middleware.process_view(self.request, self.func_viewA, (), {})
        self.assertIsNone(res)

        # PasswordChangeView is built-in view and it requires an authentication
        # Middleware redirects anonymous user with 302.
        res = self.middleware.process_view(self.request, PasswordChangeView.as_view(), (), {})
        self.assertEqual(res.status_code, 302)

        # Bview is a custom view. It requires an authentication.
        res = self.middleware.process_view(self.request, self.BView.as_view(), (), {})
        self.assertEqual(res.status_code, 302)

        # func_viewB is a custom view. It requires an authentication.
        res = self.middleware.process_view(self.request, self.func_viewB, (), {})
        self.assertEqual(res.status_code, 302)

    def test_user_access(self):
        self.request.user = self.user

        # Middleware returns None for authenticated user
        res = self.middleware.process_view(self.request, LoginView.as_view(), (), {})
        self.assertIsNone(res)

        res = self.middleware.process_view(self.request, self.AView.as_view(), (), {})
        self.assertIsNone(res)

        res = self.middleware.process_view(self.request, PasswordChangeView.as_view(), (), {})
        self.assertIsNone(res)

        res = self.middleware.process_view(self.request, self.func_viewA, (), {})
        self.assertIsNone(res)

        res = self.middleware.process_view(self.request, self.func_viewB, (), {})
        self.assertIsNone(res)
