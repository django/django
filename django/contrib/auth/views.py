import functools
import warnings

from django.conf import settings
# Avoid shadowing the login() and logout() views below.
from django.contrib.auth import (
    REDIRECT_FIELD_NAME, get_user_model, login as auth_login,
    logout as auth_logout, update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import (
    AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm,
)
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponseRedirect, QueryDict
from django.shortcuts import resolve_url
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.encoding import force_text
from django.utils.http import is_safe_url, urlsafe_base64_decode
from django.utils.six.moves.urllib.parse import urlparse, urlunparse
from django.utils.translation import ugettext as _
from django.utils.decorators import method_decorator
from django.views.generic.base import View, TemplateView
from django.views.generic.edit import FormView
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters


def deprecate_current_app(func):
    """
    Handle deprecation of the current_app parameter of the views.
    """
    @functools.wraps(func)
    def inner(*args, **kwargs):
        if 'current_app' in kwargs:
            warnings.warn(
                "Passing `current_app` as a keyword argument is deprecated. "
                "Instead the caller of `{0}` should set "
                "`request.current_app`.".format(func.__name__),
                RemovedInDjango20Warning
            )
            current_app = kwargs.pop('current_app')
            request = kwargs.get('request', None)
            if request and current_app is not None:
                request.current_app = current_app
        return func(*args, **kwargs)
    return inner


def _get_login_redirect_url(request, redirect_to):
    # Ensure the user-originating redirection URL is safe.
    if not is_safe_url(url=redirect_to, host=request.get_host()):
        return resolve_url(settings.LOGIN_REDIRECT_URL)
    return redirect_to

"""
@deprecate_current_app
@sensitive_post_parameters()
@csrf_protect
@never_cache
def login(request, template_name='registration/login.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm,
          extra_context=None, redirect_authenticated_user=False):

    # Displays the login form and handles the login action.

    redirect_to = request.POST.get(redirect_field_name, request.GET.get(redirect_field_name, ''))

    if redirect_authenticated_user and request.user.is_authenticated:
        redirect_to = _get_login_redirect_url(request, redirect_to)
        if redirect_to == request.path:
            raise ValueError(
                "Redirection loop for authenticated user detected. Check that "
                "your LOGIN_REDIRECT_URL doesn't point to a login page."
            )
        return HttpResponseRedirect(redirect_to)
    elif request.method == "POST":
        form = authentication_form(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return HttpResponseRedirect(_get_login_redirect_url(request, redirect_to))
    else:
        form = authentication_form(request)

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }
    if extra_context is not None:
        context.update(extra_context)

    return TemplateResponse(request, template_name, context)
"""


class Login(FormView):
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = 'registration/login.html'
    form_class = AuthenticationForm
    current_app = None
    extra_context = None
    """
    Displays the login form and handles the login action.
    """
    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super(Login, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Okay, security check complete. Log the user in.
        auth_login(self.request, form.get_user())
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        redirect_to = self.request.POST.get(
            self.redirect_field_name,
            self.request.GET.get(self.redirect_field_name, ''))
        # Ensure the user-originating redirection url is safe.
        if not is_safe_url(url=redirect_to, host=self.request.get_host()):
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)
            return redirect_to

    def get_context_data(self, **kwargs):
        context = super(Login, self).get_context_data(**kwargs)
        current_site = get_current_site(self.request)
        context.update({
            'redirect_field_name': self.get_success_url(),
            'site': current_site,
            'site_name': current_site.name,
            'current_app': self.current_app,
        })
        if self.extra_context is not None:
            context.update(self.extra_context)
            return context


def login(request, *args, **kwargs):
    return Login.as_view(**kwargs)(request, *args, **kwargs)


"""
@deprecate_current_app
@never_cache
def logout(request, next_page=None,
           template_name='registration/logged_out.html',
           redirect_field_name=REDIRECT_FIELD_NAME,
           extra_context=None):
    
    #Logs out the user and displays 'You are logged out' message.
    
    auth_logout(request)

    if next_page is not None:
        next_page = resolve_url(next_page)
    elif settings.LOGOUT_REDIRECT_URL:
        next_page = resolve_url(settings.LOGOUT_REDIRECT_URL)

    if (redirect_field_name in request.POST or
            redirect_field_name in request.GET):
        next_page = request.POST.get(redirect_field_name,
                                     request.GET.get(redirect_field_name))
        # Security check -- don't allow redirection to a different host.
        if not is_safe_url(url=next_page, host=request.get_host()):
            next_page = request.path

    if next_page:
        # Redirect to this page until the session has been cleared.
        return HttpResponseRedirect(next_page)

    current_site = get_current_site(request)
    context = {
        'site': current_site,
        'site_name': current_site.name,
        'title': _('Logged out')
    }
    if extra_context is not None:
        context.update(extra_context)

    return TemplateResponse(request, template_name, context)
"""


class Logout(TemplateView):
    next_page = None
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = 'registration/logged_out.html'
    current_app = None
    extra_context = None
    """
    Logs out the user and displays 'You are logged out' message.
    """
    def get(self, *args, **kwargs):
        auth_logout(self.request)
        response_kwargs = {'redirect_to': self.get_success_url()}
        if self.next_page:
            return HttpResponseRedirect(response_kwargs['redirect_to'])
        return super(Logout, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        auth_logout(self.request)
        # Redirect to this page until the session has been cleared.
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        if self.next_page is not None:
            self.next_page = resolve_url(self.next_page)

        if (self.redirect_field_name in self.request.POST or
                self.redirect_field_name in self.request.GET):
            self.next_page = self.request.POST.get(
                self.redirect_field_name,
                self.request.GET.get(self.redirect_field_name))
        # Security check -- don't allow redirection to a different host.
            if not is_safe_url(url=self.next_page, host=self.request.get_host()):
                self.next_page = self.request.path
        return self.next_page

        def get_context_data(self, **kwargs):
            context = super(Logout, self).get_context_data(**kwargs)
            current_site = get_current_site(self.request)
            context.update({
                'site': current_site,
                'site_name': current_site.name,
                'title': _('Logged out'),
                'current_app': self.current_app,
            })
            if self.extra_context is not None:
                context.update(self.extra_context)
            return context


def logout(request, *args, **kwargs):
    return Logout.as_view(**kwargs)(request, *args, **kwargs)

"""
def redirect_to_login(next, login_url=None,
                      redirect_field_name=REDIRECT_FIELD_NAME):

    #Redirects the user to the login page, passing the given 'next' page

    resolved_url = resolve_url(login_url or settings.LOGIN_URL)

    login_url_parts = list(urlparse(resolved_url))
    if redirect_field_name:
        querystring = QueryDict(login_url_parts[4], mutable=True)
        querystring[redirect_field_name] = next
        login_url_parts[4] = querystring.urlencode(safe='/')

    return HttpResponseRedirect(urlunparse(login_url_parts))
"""


class LogoutThenLogin(View):
    login_url = None
    current_app = None
    extra_context = None
    """
    Logs out the user if they are logged in. Then redirects to the log-in page.
    """
    def get(self, *args, **kwargs):
        return logout(
            self.request,
            next_page=self.get_success_url(),
            current_app=self.current_app, extra_context=self.extra_context)

    def get_success_url(self):
        if not self.login_url:
            self.login_url = settings.LOGIN_URL
            login_url = resolve_url(self.login_url)
        return login_url


def redirect_to_login(request, *args, **kwargs):
    return LogoutThenLogin.as_view(**kwargs)(request, *args, **kwargs)


"""
@deprecate_current_app
@csrf_protect
def password_reset(request,
                   template_name='registration/password_reset_form.html',
                   email_template_name='registration/password_reset_email.html',
                   subject_template_name='registration/password_reset_subject.txt',
                   password_reset_form=PasswordResetForm,
                   token_generator=default_token_generator,
                   post_reset_redirect=None,
                   from_email=None,
                   extra_context=None,
                   html_email_template_name=None,
                   extra_email_context=None):
    if post_reset_redirect is None:
        post_reset_redirect = reverse('password_reset_done')
    else:
        post_reset_redirect = resolve_url(post_reset_redirect)
    if request.method == "POST":
        form = password_reset_form(request.POST)
        if form.is_valid():
            opts = {
                'use_https': request.is_secure(),
                'token_generator': token_generator,
                'from_email': from_email,
                'email_template_name': email_template_name,
                'subject_template_name': subject_template_name,
                'request': request,
                'html_email_template_name': html_email_template_name,
                'extra_email_context': extra_email_context,
            }
            form.save(**opts)
            return HttpResponseRedirect(post_reset_redirect)
    else:
        form = password_reset_form()
    context = {
        'form': form,
        'title': _('Password reset'),
    }
    if extra_context is not None:
        context.update(extra_context)

    return TemplateResponse(request, template_name, context)
"""

class PasswordReset(FormView):
    is_admin_site = False
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    password_reset_form = PasswordResetForm
    token_generator = default_token_generator
    post_reset_redirect = None
    from_email = None
    current_app = None
    extra_context = None
    html_email_template_name = None

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        return super(PasswordReset, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': self.token_generator,
            'from_email': self.from_email,
            'email_template_name': self.email_template_name,
            'subject_template_name': self.subject_template_name,
            'request': self.request,
            'html_email_template_name': self.html_email_template_name,
        }
        if self.is_admin_site:
            opts = dict(opts, domain_override=self.request.get_host())
            form.save(**opts)
        return HttpResponseRedirect(self.get_success_url())

    def get_form_class(self):
        return self.password_reset_form

    def get_success_url(self):
        if self.post_reset_redirect is None:
            self.post_reset_redirect = reverse('password_reset_done')
        else:
            self.post_reset_redirect = resolve_url(self.post_reset_redirect)
        return self.post_reset_redirect

    def get_context_data(self, **kwargs):
        context = super(PasswordReset, self).get_context_data(**kwargs)
        context.update(
            'title': _('Password reset'),
            'current_app': self.current_app,
        })
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context


def password_reset(request, *args, **kwargs):
    return PasswordReset.as_view(**kwargs)(request, *args, **kwargs)


"""
@deprecate_current_app
def password_reset_done(request,
                        template_name='registration/password_reset_done.html',
                        extra_context=None):
    context = {
        'title': _('Password reset sent'),
    }
    if extra_context is not None:
        context.update(extra_context)

    return TemplateResponse(request, template_name, context)
"""


class PasswordResetDone(TemplateView):
    template_name = 'registration/password_reset_done.html'
    current_app = None
    extra_context = None

    def get_context_data(self, **kwargs):
        context = super(PasswordResetDone, self).get_context_data(**kwargs)
        context.update({
            'title': _('Password reset successful'),
            'current_app': self.current_app,
        })
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context


def password_reset_done(request, *args, **kwargs):
    return PasswordResetDone.as_view(**kwargs)(request, *args, **kwargs)

"""
# Doesn't need csrf_protect since no-one can guess the URL
@sensitive_post_parameters()
@never_cache
@deprecate_current_app
def password_reset_confirm(request, uidb64=None, token=None,
                           template_name='registration/password_reset_confirm.html',
                           token_generator=default_token_generator,
                           set_password_form=SetPasswordForm,
                           post_reset_redirect=None,
                           extra_context=None):
    
    #View that checks the hash in a password reset link and presents a
    #form for entering a new password.
    
    usermodel = get_user_model()
    assert uidb64 is not None and token is not None  # checked by URLconf
    if post_reset_redirect is None:
        post_reset_redirect = reverse('password_reset_complete')
    else:
        post_reset_redirect = resolve_url(post_reset_redirect)
    try:
        # urlsafe_base64_decode() decodes to bytestring on Python 3
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = usermodel._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, usermodel.DoesNotExist):
        user = None

    if user is not None and token_generator.check_token(user, token):
        validlink = True
        title = _('Enter new password')
        if request.method == 'POST':
            form = set_password_form(user, request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(post_reset_redirect)
        else:
            form = set_password_form(user)
    else:
        validlink = False
        form = None
        title = _('Password reset unsuccessful')
    context = {
        'form': form,
        'title': title,
        'validlink': validlink,
    }
    if extra_context is not None:
        context.update(extra_context)

    return TemplateResponse(request, template_name, context)
"""


class PasswordResetConfirm(FormView):
    uidb64 = None
    token = None
    template_name = 'registration/password_reset_confirm.html'
    token_generator = default_token_generator
    set_password_form = SetPasswordForm
    post_reset_redirect = None
    current_app = None
    extra_context = None
    user = None
    validlink = False
    form = None
    title = _('Password reset unsuccessful')
    """
    View that checks the hash in a password reset link and presents a
    form for entering a new password.
    """
    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        # checked by URLconf
        assert self.uidb64 is not None and self.token is not None
        usermodel = get_user_model()
        try:
            uid = urlsafe_base64_decode(self.uidb64)
            self.user = usermodel._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, usermodel.DoesNotExist):
            self.user = None
        return super(PasswordResetConfirm, self).dispatch(request, *args, **kwargs)

    def get(self, *args, **kwargs):
        if self.user is not None and self.token_generator.check_token(self.user, self.token):
            self.validlink = True
            self.title = _('Enter new password')
        return super(PasswordResetConfirm, self).get(*args, **kwargs)

    def form_valid(self, form):
        form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_form(self, form_class):
        return form_class(self.user, **self.get_form_kwargs())

    def get_form_class(self):
        return self.set_password_form

    def get_success_url(self):
        if self.post_reset_redirect is None:
            self.post_reset_redirect = reverse('password_reset_complete')
        else:
            self.post_reset_redirect = resolve_url(self.post_reset_redirect)
        return self.post_reset_redirect

    def get_context_data(self, **kwargs):
        context = super(PasswordResetConfirm, self).get_context_data(**kwargs)
        context.update({
            'title': self.title,
            'validlink': self.validlink,
            'current_app': self.current_app,
        })
        if self.extra_context is not None:
            context.update(self.extra_context)
            if self.user is None:
                context.update({
                    'form': None,
                })
        return context


def password_reset_confirm(request, *args, **kwargs):
    try:
        uidb64 = args[1] or None
        token = args[2] or None
        print(uidb64, token)
        if uidb64 and token:
            kwargs.update({
                'uidb64': uidb64,
                'token': token,
            })
    except:
        pass
    return PasswordResetConfirm.as_view(**kwargs)(request, *args, **kwargs)

"""
@deprecate_current_app
def password_reset_complete(request,
                            template_name='registration/password_reset_complete.html',
                            extra_context=None):
    context = {
        'login_url': resolve_url(settings.LOGIN_URL),
        'title': _('Password reset complete'),
    }
    if extra_context is not None:
        context.update(extra_context)

    return TemplateResponse(request, template_name, context)
"""


class PasswordResetComplete(TemplateView):
    template_name = 'registration/password_reset_complete.html'
    current_app = None
    extra_context = None

    def get_context_data(self, **kwargs):
        context = super(PasswordResetComplete, self).get_context_data(**kwargs)
        context.update({
            'login_url': resolve_url(settings.LOGIN_URL),
            'title': _('Password reset complete'),
            'current_app': self.current_app,
        })
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context


def password_reset_complete(request, *args, **kwargs):
    return PasswordResetComplete.as_view(**kwargs)(request, *args, **kwargs)

"""
@sensitive_post_parameters()
@csrf_protect
@login_required
@deprecate_current_app
def password_change(request,
                    template_name='registration/password_change_form.html',
                    post_change_redirect=None,
                    password_change_form=PasswordChangeForm,
                    extra_context=None):
    if post_change_redirect is None:
        post_change_redirect = reverse('password_change_done')
    else:
        post_change_redirect = resolve_url(post_change_redirect)
    if request.method == "POST":
        form = password_change_form(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            # Updating the password logs out all other sessions for the user
            # except the current one.
            update_session_auth_hash(request, form.user)
            return HttpResponseRedirect(post_change_redirect)
    else:
        form = password_change_form(user=request.user)
    context = {
        'form': form,
        'title': _('Password change'),
    }
    if extra_context is not None:
        context.update(extra_context)

    return TemplateResponse(request, template_name, context)
"""


class PasswordChange(FormView):
    template_name = 'registration/password_change_form.html'
    post_change_redirect = None
    password_change_form = PasswordChangeForm
    current_app = None
    extra_context = None

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(PasswordChange, self).dispatch(self.request, *args, **kwargs)

    def get_success_url(self):
        if self.post_change_redirect is None:
            self.post_change_redirect = reverse('password_change_done')
        else:
            form = set_password_form(user)
            self.post_change_redirect = resolve_url(self.post_change_redirect)
        return self.post_change_redirect

    def get_form(self, form_class):
        return form_class(self.request.user, **self.get_form_kwargs())

    def get_form_class(self):
        return self.password_change_form

    def form_valid(self, form):
        form.save()
        # Updating the password logs out all other sessions for the user
        # except the current one if
        # django.contrib.auth.middleware.SessionAuthenticationMiddleware
        # is enabled.
        update_session_auth_hash(self.request, form.user)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(PasswordChange, self).get_context_data(**kwargs)
        context.update({
            'title': _('Password change'),
            'current_app': self.current_app,
        })
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context


def password_change(request, *args, **kwargs):
    return PasswordChange.as_view(**kwargs)(request, *args, **kwargs)

"""
@login_required
@deprecate_current_app
def password_change_done(request,
                         template_name='registration/password_change_done.html',
                         extra_context=None):
    context = {
        'title': _('Password change successful'),
    }
    if extra_context is not None:
        context.update(extra_context)

    return TemplateResponse(request, template_name, context)
"""


class PasswordChangeDone(TemplateView):
    template_name = 'registration/password_change_done.html'
    current_app = None
    extra_context = None

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(PasswordChangeDone, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(PasswordChangeDone, self).get_context_data(**kwargs)
        context.update({
            'title': _('Password change successful'),
            'current_app': self.current_app,
        })
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context


def password_change_done(request, *args, **kwargs):
    return PasswordChangeDone.as_view(**kwargs)(request, *args, **kwargs)

#############

# 4 views for password reset:
# - password_reset sends the mail
# - password_reset_done shows a success message for the above
# - password_reset_confirm checks the link the user clicked and
#   prompts for a new password
# - password_reset_complete shows a success message for the above

