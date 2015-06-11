from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.utils import six
from django.utils.encoding import force_text


class UserPassesTestMixin(object):
    """
    Mixin for class-based views that checks that the user passes the given by
    the class method `test_func`.
    """
    login_url = None
    permission_denied_message = ''
    raise_exception = False
    redirect_field_name = REDIRECT_FIELD_NAME

    def dispatch(self, request, *args, **kwargs):
        user_test_result = self.get_test_func()(request.user)

        if not user_test_result:
            return self.handle_no_permission(request)

        return super(UserPassesTestMixin, self).dispatch(request, *args, **kwargs)

    def get_test_func(self):
        return getattr(self, "test_func")

    def test_func(self, user):
        raise NotImplementedError(
            '{0} is missing implementation of the '
            'test_func method.'.format(self.__class__.__name__)
        )

    def get_login_url(self):
        """
        Override this method to customize the login_url.
        """
        login_url = self.login_url or settings.LOGIN_URL
        if not login_url:
            raise ImproperlyConfigured(
                'Define {0}.login_url or settings.LOGIN_URL or override '
                '{0}.get_login_url().'.format(self.__class__.__name__)
            )
        return force_text(login_url)

    def get_permission_denied_message(self):
        return self.permission_denied_message

    def get_redirect_field_name(self):
        """
        Override this method to customize the redirect_field_name.
        """
        return self.redirect_field_name

    def handle_no_permission(self, request):
        # In case the 403 handler should be called, raise the exception.
        if self.raise_exception:
            raise PermissionDenied(self.get_permission_denied_message())
        return redirect_to_login(request.get_full_path(), self.get_login_url(), self.get_redirect_field_name())


class LoginRequiredMixin(UserPassesTestMixin):
    """
    Mixin for class-based views that checks that the user is logged in,
    redirecting to the login page if necessary.
    """

    def test_func(self, user):
        return user.is_authenticated()


class PermissionRequiredMixin(UserPassesTestMixin):
    """
    Mixin for class-based views that checks whether a user has a particular
    permission enabled, redirecting to the login page if necessary.

    If the raise_exception parameter is given, the PermissionDenied exception
    is raised.
    """
    permission_required = None

    def test_func(self, user):
        if isinstance(self.permission_required, six.string_types):
            perms = (self.permission_required, )
        else:
            perms = self.permission_required
        return user.has_perms(perms)
