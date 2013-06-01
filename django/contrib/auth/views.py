try:
    from urllib.parse import urlparse, urlunparse
except ImportError:     # Python 2
    from urlparse import urlparse, urlunparse

from django.conf import settings
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect, QueryDict
from django.utils.http import base36_to_int, is_safe_url
from django.utils.translation import ugettext as _
from django.utils.functional import lazy
from django.shortcuts import resolve_url
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic import FormView, TemplateView, RedirectView

# Avoid shadowing the login() and logout() views below.
from django.contrib.auth import REDIRECT_FIELD_NAME, login as auth_login, logout as auth_logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm, PasswordChangeForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.models import get_current_site


resolve_url_lazy = lazy(resolve_url, str)


def redirect_to_login(next, login_url=None,
                      redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Redirects the user to the login page, passing the given 'next' page
    """
    resolved_url = resolve_url(login_url or settings.LOGIN_URL)

    login_url_parts = list(urlparse(resolved_url))
    if redirect_field_name:
        querystring = QueryDict(login_url_parts[4], mutable=True)
        querystring[redirect_field_name] = next
        login_url_parts[4] = querystring.urlencode(safe='/')

    return HttpResponseRedirect(urlunparse(login_url_parts))


def deprecated_kwarg(old_kwarg, default=None):
    """
    Returns a function that will get a value of self.kwargs.  If
    that value exists, it will also raise a deprecation message.
    """
    def inner(self):
        if old_kwarg in self.kwargs:
            # XXX: raise deprecation?
            return self.kwargs[old_kwarg]
        return default
    return inner


def deprecated_kwargp(*args, **kwargs):
    """
    Wraps deprecated_kwarg in a property.
    """
    return property(deprecated_kwarg(*args, **kwargs))


def deprecated_url_kwargp(old_kwarg, default=None):
    @property
    def inner(self):
        url = deprecated_kwarg(old_kwarg)(self)
        if url:
            return resolve_url(url)
        return default
    return inner


class CurrentSiteMixin(object):
    def get_current_site(self):
        return get_current_site(self.request)

    def get_context_data(self, **kwargs):
        kwargs = super(CurrentSiteMixin, self).get_context_data(**kwargs)
        current_site = self.get_current_site()
        kwargs.update({
            'site': current_site,
            'site_name': current_site.name,
        })
        return kwargs


class BackwardsCompatibleRenderingMixin(object):
    """
    Add backwards-compatible support for the extra_context and current_app
    kwargs that the function views supported.
    """
    current_app = deprecated_kwargp('current_app')

    def render_to_response(self, context, **kwargs):
        # extra_context is in render_to_response instead of get_context_data
        # because it needs to be applied last.
        extra_context = deprecated_kwarg('extra_context')(self)
        if extra_context:
            context.update(extra_context)
        kwargs['current_app'] = self.current_app
        return super(BackwardsCompatibleRenderingMixin, self).render_to_response(context, **kwargs)


class WithNextUrlMixin(object):
    """
    Mixin for providing the redirect_field_name kwargs functionality.  It works
    as a mixin for both FormView and RedirectView.
    """
    redirect_field_name = deprecated_kwargp('redirect_field_name', REDIRECT_FIELD_NAME)

    def get_next_url(self):
        redirect_to = None
        if self.redirect_field_name in self.request.REQUEST:
            redirect_to = self.request.REQUEST[self.redirect_field_name]
        elif self.redirect_field_name in self.kwargs:
            redirect_to = self.kwargs[self.redirect_field_name]

        if redirect_to:
            if is_safe_url(redirect_to, host=self.request.get_host()):
                return redirect_to
            else:
                # XXX: This is the behavior in the logout function view.  I
                # don't think it should actually redirect if the next_page is
                # invalid though.
                return self.request.path

    # This mixin can be mixed with FormViews and RedirectViews. They
    # each use a different method to get the URL to redirect to, so we
    # need to provide both methods.
    def get_success_url(self):
        return self.get_next_url() or super(WithNextUrlMixin, self).get_success_url()

    def get_redirect_url(self, **kwargs):
        return self.get_next_url() or super(WithNextUrlMixin, self).get_redirect_url(**kwargs)


def DecoratorMixin(decorator):
    """
    Converts a decorator written for a function view into a mixin for a
    class-based view. ::

        LoginRequiredMixin = DecoratorMixin(login_required)

        class MyView(LoginRequiredMixin):
            pass

        class SomeView(DecoratorMixin(some_decorator),
                       DecoratorMixin(something_else)):
            pass

    """

    class Mixin(object):
        __doc__ = decorator.__doc__

        @classmethod
        def as_view(cls, *args, **kwargs):
            view = super(Mixin, cls).as_view(*args, **kwargs)
            return decorator(view)

    Mixin.__name__ = str('DecoratorMixin(%s)' % decorator.__name__)
    return Mixin


NeverCacheMixin = DecoratorMixin(never_cache)
CsrfProtectMixin = DecoratorMixin(csrf_protect)
LoginRequiredMixin = DecoratorMixin(login_required)
SensitivePostParametersMixin = DecoratorMixin(
    sensitive_post_parameters('password', 'old_password', 'password1',
                              'password2', 'new_password1', 'new_password2')
)


class AuthDecoratorsMixin(NeverCacheMixin, CsrfProtectMixin, SensitivePostParametersMixin):
    pass


class LoginView(AuthDecoratorsMixin, BackwardsCompatibleRenderingMixin, CurrentSiteMixin, WithNextUrlMixin, FormView):
    """
    Displays the login form and handles the login action.
    """
    form_class = deprecated_kwargp('authentication_form', AuthenticationForm)
    template_name = deprecated_kwargp('template_name', 'registration/login.html')

    @property
    def success_url(self):
        # We have to use this instead of resolve_url_lazy in order to allow the
        # tests to override the LOGIN_REDIRECT_URL setting.
        return resolve_url(settings.LOGIN_REDIRECT_URL)

    def form_valid(self, form):
        auth_login(self.request, form.get_user())
        return super(LoginView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs = super(LoginView, self).get_context_data(**kwargs)
        kwargs.update({
            self.redirect_field_name: self.request.REQUEST.get(
                self.redirect_field_name, '',
            ),
        })
        return kwargs

login = LoginView.as_view()


class LogoutView(NeverCacheMixin, BackwardsCompatibleRenderingMixin, CurrentSiteMixin, WithNextUrlMixin, TemplateView, RedirectView):
    """
    Logs out the user and displays 'You are logged out' message.
    """
    template_name = deprecated_kwargp('template_name', 'registration/logged_out.html')
    url = deprecated_url_kwargp('next_page')
    permanent = False

    def get(self, *args, **kwargs):
        auth_logout(self.request)
        # If we have a URL to redirect to, do it. Otherwise render the logged-out template.
        if self.get_redirect_url(**kwargs):
            return RedirectView.get(self, *args, **kwargs)
        else:
            return TemplateView.get(self, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # XXX: None of the other views provide a title, is this legacy code for
        # the admin site?
        kwargs['title'] = _('Logged Out')
        return super(LogoutView, self).get_context_data(**kwargs)

logout = LogoutView.as_view()
logout_then_login = LogoutView.as_view(
    url=resolve_url_lazy(settings.LOGIN_URL)
)


# 4 views for password reset:
# - password_reset sends the mail
# - password_reset_done shows a success message for the above
# - password_reset_confirm checks the link the user clicked and
#   prompts for a new password
# - password_reset_complete shows a success message for the above


class PasswordResetView(BackwardsCompatibleRenderingMixin, CsrfProtectMixin, FormView):
    template_name = deprecated_kwargp('template_name', 'registration/password_reset_form.html')
    token_generator = deprecated_kwargp('token_generator', default_token_generator)
    subject_template_name = deprecated_kwargp('subject_template_name', 'registration/password_reset_subject.txt')
    email_template_name = deprecated_kwargp('email_template_name', 'registration/password_reset_email.html')
    from_email = deprecated_kwargp('from_email')
    form_class = deprecated_kwargp('password_change_form', PasswordResetForm)
    success_url = deprecated_url_kwargp('post_reset_redirect',
                                        reverse_lazy('password_reset_done'))

    def get_form_save_kwargs(self):
        kwargs = {
            'subject_template_name': self.subject_template_name,
            'email_template_name': self.email_template_name,
            'token_generator': self.token_generator,
            'from_email': self.from_email,
            'request': self.request,
        }
        # XXX: move to the admin view that actually uses this?
        if deprecated_kwarg('is_admin_site')(self):
            kwargs['domain_override'] = self.request.get_host()
        return kwargs

    def form_valid(self, form):
        form.save(**self.get_form_save_kwargs())
        return super(PasswordResetView, self).form_valid(form)

password_reset = PasswordResetView.as_view()


class PasswordResetDoneView(BackwardsCompatibleRenderingMixin, TemplateView):
    template_name = deprecated_kwargp('template_name', 'registration/password_reset_done.html')

password_reset_done = PasswordResetDoneView.as_view()


class PasswordResetConfirmView(BackwardsCompatibleRenderingMixin, AuthDecoratorsMixin, FormView):
    """
    View that checks the hash in a password reset link and presents a
    form for entering a new password.
    """
    template_name = deprecated_kwargp('template_name', 'registration/password_reset_confirm.html')
    token_generator = deprecated_kwargp('token_generator', default_token_generator)
    form_class = deprecated_kwargp('set_password_form', SetPasswordForm)
    success_url = deprecated_url_kwargp('post_reset_redirect',
                                        reverse_lazy('password_reset_complete'))

    def dispatch(self, *args, **kwargs):
        assert self.kwargs.get('uidb36') is not None and self.kwargs.get('token') is not None
        self.user = self.get_user()
        return super(PasswordResetConfirmView, self).dispatch(*args, **kwargs)

    def get_user(self):
        User = get_user_model()
        try:
            uid_int = base36_to_int(self.kwargs.get('uidb36'))
            return User._default_manager.get(pk=uid_int)
        except (ValueError, OverflowError, User.DoesNotExist):
            return None

    def valid_link(self):
        user = self.user
        return user is not None and self.token_generator.check_token(user, self.kwargs.get('token'))

    def get_form_kwargs(self):
        kwargs = super(PasswordResetConfirmView, self).get_form_kwargs()
        kwargs['user'] = self.user
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs = super(PasswordResetConfirmView, self).get_context_data(**kwargs)
        if self.valid_link():
            kwargs['validlink'] = True
        else:
            kwargs['validlink'] = False
            kwargs['form'] = None
        return kwargs

    def form_valid(self, form):
        if not self.valid_link():
            return self.form_invalid(form)
        self.save_form(form)
        return super(PasswordResetConfirmView, self).form_valid(form)

    def save_form(self, form):
        return form.save()

password_reset_confirm = PasswordResetConfirmView.as_view()


class PasswordResetCompleteView(BackwardsCompatibleRenderingMixin, TemplateView):
    template_name = deprecated_kwargp('template_name', 'registration/password_reset_complete.html')
    login_url = resolve_url_lazy(settings.LOGIN_URL)

    def get_login_url(self):
        return self.login_url

    def get_context_data(self, **kwargs):
        kwargs = super(PasswordResetCompleteView, self).get_context_data(**kwargs)
        kwargs['login_url'] = self.get_login_url()
        return kwargs

password_reset_complete = PasswordResetCompleteView.as_view()


class PasswordChangeView(BackwardsCompatibleRenderingMixin, LoginRequiredMixin, AuthDecoratorsMixin, FormView):
    template_name = deprecated_kwargp('template_name', 'registration/password_change_form.html')
    form_class = deprecated_kwargp('password_reset_form', PasswordChangeForm)
    success_url = deprecated_url_kwargp('post_change_redirect',
                                        reverse_lazy('password_change_done'))

    def get_form_kwargs(self):
        kwargs = super(PasswordChangeView, self).get_form_kwargs()
        kwargs['user'] = self.get_user()
        return kwargs

    def get_user(self):
        return self.request.user

    def form_valid(self, form):
        form.save()
        return super(PasswordChangeView, self).form_valid(form)

password_change = PasswordChangeView.as_view()


class PasswordChangeDoneView(BackwardsCompatibleRenderingMixin, LoginRequiredMixin, TemplateView):
    template_name = deprecated_kwargp('template_name', 'registration/password_change_done.html')

password_change_done = PasswordChangeDoneView.as_view()
