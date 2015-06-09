from django.contrib.auth import models
from django.contrib.auth.mixins import (
    LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin,
)
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.views.generic import View

from .test_views import AuthViewsTestCase


class EmptyResponseView(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse()


class UserTestAlwaysTrueView(UserPassesTestMixin, EmptyResponseView):

    def test_func(self, user):
        return True


class UserTestAlwaysFalseView(UserPassesTestMixin, EmptyResponseView):

    def test_func(self, user):
        return False


class UserPassesTestTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()

    def test_redirect(self, view=None, url='/accounts/login/?next=/rand'):
        if not view:
            view = UserTestAlwaysFalseView.as_view()
        request = self.factory.get('/rand')
        request.user = AnonymousUser()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, url)

    def test_custom_redirect_url(self):
        class AView(UserTestAlwaysFalseView):
            login_url = '/login/'

        self.test_redirect(AView.as_view(), '/login/?next=/rand')

    def test_custom_redirect_parameter(self):
        class AView(UserTestAlwaysFalseView):
            redirect_field_name = 'goto'

        self.test_redirect(AView.as_view(), '/accounts/login/?goto=/rand')

    def test_no_redirect_parameter(self):
        class AView(UserTestAlwaysFalseView):
            redirect_field_name = None

        self.test_redirect(AView.as_view(), '/accounts/login/')

    def test_raise_exception(self):
        class AView(UserTestAlwaysFalseView):
            raise_exception = True

        request = self.factory.get('/rand')
        request.user = AnonymousUser()
        self.assertRaises(PermissionDenied, AView.as_view(), request)

    def test_user_passes(self):
        view = UserTestAlwaysTrueView.as_view()
        request = self.factory.get('/rand')
        request.user = AnonymousUser()
        response = view(request)
        self.assertEqual(response.status_code, 200)


class LoginRequiredMixinTestCase(AuthViewsTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = models.User.objects.create(username='joe', password='qwerty')
        cls.factory = RequestFactory()

    def test_login_required(self):
        """
        Check that login_required works on a simple view wrapped in a
        login_required decorator.
        """
        class AView(LoginRequiredMixin, EmptyResponseView):
            pass

        view = AView.as_view()

        request = self.factory.get('/rand')
        request.user = AnonymousUser()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual('/accounts/login/?next=/rand', response.url)
        request = self.factory.get('/rand')
        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, 200)


class PermissionsRequiredMixinTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = models.User.objects.create(username='joe', password='qwerty')
        cls.factory = RequestFactory()
        # Add permissions auth.add_customuser and auth.change_customuser
        perms = models.Permission.objects.filter(codename__in=('add_customuser', 'change_customuser'))
        cls.user.user_permissions.add(*perms)

    def test_many_permissions_pass(self):
        class AView(PermissionRequiredMixin, EmptyResponseView):
            permission_required = ['auth.add_customuser', 'auth.change_customuser']

        request = self.factory.get('/rand')
        request.user = self.user
        resp = AView.as_view()(request)
        self.assertEqual(resp.status_code, 200)

    def test_single_permission_pass(self):
        class AView(PermissionRequiredMixin, EmptyResponseView):
            permission_required = 'auth.add_customuser'

        request = self.factory.get('/rand')
        request.user = self.user
        resp = AView.as_view()(request)
        self.assertEqual(resp.status_code, 200)

    def test_permissioned_denied_redirect(self):
        class AView(PermissionRequiredMixin, EmptyResponseView):
            permission_required = ['auth.add_customuser', 'auth.change_customuser', 'non-existent-permission']

        request = self.factory.get('/rand')
        request.user = self.user
        resp = AView.as_view()(request)
        self.assertEqual(resp.status_code, 302)

    def test_permissioned_denied_exception_raised(self):
        class AView(PermissionRequiredMixin, EmptyResponseView):
            permission_required = ['auth.add_customuser', 'auth.change_customuser', 'non-existent-permission']
            raise_exception = True

        request = self.factory.get('/rand')
        request.user = self.user
        self.assertRaises(PermissionDenied, AView.as_view(), request)
