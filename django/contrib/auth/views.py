try:
    from urllib.parse import urlparse, urlunparse
except ImportError:     # Python 2
    from urlparse import urlparse, urlunparse

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, QueryDict
from django.template.response import TemplateResponse
from django.utils.http import base36_to_int
from django.utils.translation import ugettext as _
from django.shortcuts import resolve_url
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic import FormView

# Avoid shadowing the login() and logout() views below.
from django.contrib.auth import REDIRECT_FIELD_NAME, login as auth_login, logout as auth_logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm, PasswordChangeForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.models import get_current_site


class LoginView(FormView):
    """Class-based login view."""
    #: Template name.
    template_name = 'registration/login.html'

    #: Name of the field passed via GET which sets the redirection URL.
    redirect_field_name = REDIRECT_FIELD_NAME

    #: Success URL.
    success_url = '/accounts/profile/'

    #: Authentication form class.
    form_class = AuthenticationForm

    #: URL where to redirect in case of success.
    #:
    #: .. warning::
    #:
    #:    This option is deprecated. It is a duplicate of of ``success_url``
    #:    which remains for backward-compatibility purpose. Use ``success_url``
    #:    whenever possible.
    redirect_to = None

    #: Authentication form class.
    #:
    #: If set, has precedence over standard ``form_class``.
    #:
    #: .. warning::
    #:
    #:    This option is deprecated. It is a duplicate of of ``form_class``
    #:    which remains for backward-compatibility purpose. Use ``form_class``
    #:    whenever possible.
    authentication_form = None

    #: A hint indicating which application contains the current view.
    #: See the namespaced URL resolution strategy for more information.
    #:
    #: .. note::
    #:
    #:    This argument is provided for backward-compatibility. Generic
    #     class-based views (i.e. TemplateResponseMixin) don't use it.
    current_app = None

    #: Extra context.
    #:
    #: .. note::
    #:
    #:    This argument is provided for backward-compatibility. Generic
    #     class-based views (i.e. TemplateResponseMixin) don't use it.
    extra_context = None

    def get_form_class(self):
        """Return self.authentication_form or self.form_class."""
        if self.authentication_form:
            return self.authentication_form
        else:
            return super(LoginView, self).get_form_class()

    def validate_success_url(self, value):
        """Raise ValidationError if success URL is invalid, else return URL."""
        if not value:
            raise ValidationError('Redirect URL is required')
        # Heavier security check -- don't allow redirection to a different
        # host.
        netloc = urlparse(value)[1]
        if netloc and netloc != self.request.get_host():
            raise ValidationError('URL belongs to another host.')
        return value

    def get_success_url(self):
        """Get success URL from request parameters or settings.

        As with any FormView, you can also customize the success URL via the
        view's ``success_url`` argument.

        """
        # Try request parameters, with validation.
        candidate_url = self.request.REQUEST.get(self.redirect_field_name, '')
        try:
            success_url = self.validate_success_url(candidate_url)
        except ValidationError:
            # Backward compatibility: if provided, ``redirect_to`` overrides
            # ``success_url``
            if self.redirect_to:
                self.success_url = self.redirect_to
            # Try parent's get_success_url(): read views's ``success_url``.
            try:
                success_url = super(LoginView, self).get_success_url()
            except ImproperlyConfigured:
                # Fallback to settings.
                success_url = settings.LOGIN_REDIRECT_URL
        return success_url

    def set_test_cookie(self):
        """Set test cookie."""
        self.request.session.set_test_cookie()

    def unset_test_cookie(self):
        """Remove test cookie."""
        if self.request.session.test_cookie_worked():
            self.request.session.delete_test_cookie()

    def login(self, user):
        """Actually log user in."""
        return auth_login(self.request, user)

    def form_valid(self, form):
        # Log the user in.
        self.login(form.get_user())
        # Clean test cookie if necessary.
        self.unset_test_cookie()
        # Redirect.
        return super(LoginView, self).form_valid(form)

    def get(self, request, *args, **kwargs):
        """Handle GET requests."""
        self.request = request
        self.set_test_cookie()
        return super(LoginView, self).get(request, *args, **kwargs)

    def get_current_site(self):
        """Return current site, for use in context data.

        Returned value is a :py:class:`django.contrib.sites.models.Site`
        instance.

        """
        return get_current_site(self.request)

    def get_context_data(self, **kwargs):
        data = super(LoginView, self).get_context_data(**kwargs)
        current_site = self.get_current_site()
        data[self.redirect_field_name] = self.redirect_to
        data['site'] = current_site
        data['site_name'] = current_site.name
        if self.extra_context is not None:
            data.update(self.extra_context)
        return data

    def render_to_response(self, context, **response_kwargs):
        """Return response."""
        if self.current_app:
            response_kwargs['current_app'] = self.current_app
        return super(LoginView, self).render_to_response(context,
                                                         **response_kwargs)


@sensitive_post_parameters()
@csrf_protect
@never_cache
def login(request, *args, **kwargs):
    """Pre-configured and pre-decorated login view for backward-compatibility.

    """
    view = LoginView.as_view(*args, **kwargs)
    return view(request)


def logout(request, next_page=None,
           template_name='registration/logged_out.html',
           redirect_field_name=REDIRECT_FIELD_NAME,
           current_app=None, extra_context=None):
    """
    Logs out the user and displays 'You are logged out' message.
    """
    auth_logout(request)
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    if redirect_to:
        netloc = urlparse(redirect_to)[1]
        # Security check -- don't allow redirection to a different host.
        if not (netloc and netloc != request.get_host()):
            return HttpResponseRedirect(redirect_to)

    if next_page is None:
        current_site = get_current_site(request)
        context = {
            'site': current_site,
            'site_name': current_site.name,
            'title': _('Logged out')
        }
        if extra_context is not None:
            context.update(extra_context)
        return TemplateResponse(request, template_name, context,
                                current_app=current_app)
    else:
        # Redirect to this page until the session has been cleared.
        return HttpResponseRedirect(next_page or request.path)


def logout_then_login(request, login_url=None, current_app=None, extra_context=None):
    """
    Logs out the user if he is logged in. Then redirects to the log-in page.
    """
    if not login_url:
        login_url = settings.LOGIN_URL
    login_url = resolve_url(login_url)
    return logout(request, login_url, current_app=current_app, extra_context=extra_context)


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


# 4 views for password reset:
# - password_reset sends the mail
# - password_reset_done shows a success message for the above
# - password_reset_confirm checks the link the user clicked and
#   prompts for a new password
# - password_reset_complete shows a success message for the above

@csrf_protect
def password_reset(request, is_admin_site=False,
                   template_name='registration/password_reset_form.html',
                   email_template_name='registration/password_reset_email.html',
                   subject_template_name='registration/password_reset_subject.txt',
                   password_reset_form=PasswordResetForm,
                   token_generator=default_token_generator,
                   post_reset_redirect=None,
                   from_email=None,
                   current_app=None,
                   extra_context=None):
    if post_reset_redirect is None:
        post_reset_redirect = reverse('django.contrib.auth.views.password_reset_done')
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
            }
            if is_admin_site:
                opts = dict(opts, domain_override=request.get_host())
            form.save(**opts)
            return HttpResponseRedirect(post_reset_redirect)
    else:
        form = password_reset_form()
    context = {
        'form': form,
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
                            current_app=current_app)


def password_reset_done(request,
                        template_name='registration/password_reset_done.html',
                        current_app=None, extra_context=None):
    context = {}
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
                            current_app=current_app)


# Doesn't need csrf_protect since no-one can guess the URL
@sensitive_post_parameters()
@never_cache
def password_reset_confirm(request, uidb36=None, token=None,
                           template_name='registration/password_reset_confirm.html',
                           token_generator=default_token_generator,
                           set_password_form=SetPasswordForm,
                           post_reset_redirect=None,
                           current_app=None, extra_context=None):
    """
    View that checks the hash in a password reset link and presents a
    form for entering a new password.
    """
    UserModel = get_user_model()
    assert uidb36 is not None and token is not None  # checked by URLconf
    if post_reset_redirect is None:
        post_reset_redirect = reverse('django.contrib.auth.views.password_reset_complete')
    try:
        uid_int = base36_to_int(uidb36)
        user = UserModel.objects.get(id=uid_int)
    except (ValueError, OverflowError, UserModel.DoesNotExist):
        user = None

    if user is not None and token_generator.check_token(user, token):
        validlink = True
        if request.method == 'POST':
            form = set_password_form(user, request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(post_reset_redirect)
        else:
            form = set_password_form(None)
    else:
        validlink = False
        form = None
    context = {
        'form': form,
        'validlink': validlink,
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
                            current_app=current_app)


def password_reset_complete(request,
                            template_name='registration/password_reset_complete.html',
                            current_app=None, extra_context=None):
    context = {
        'login_url': resolve_url(settings.LOGIN_URL)
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
                            current_app=current_app)


@sensitive_post_parameters()
@csrf_protect
@login_required
def password_change(request,
                    template_name='registration/password_change_form.html',
                    post_change_redirect=None,
                    password_change_form=PasswordChangeForm,
                    current_app=None, extra_context=None):
    if post_change_redirect is None:
        post_change_redirect = reverse('django.contrib.auth.views.password_change_done')
    if request.method == "POST":
        form = password_change_form(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(post_change_redirect)
    else:
        form = password_change_form(user=request.user)
    context = {
        'form': form,
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
                            current_app=current_app)


@login_required
def password_change_done(request,
                         template_name='registration/password_change_done.html',
                         current_app=None, extra_context=None):
    context = {}
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
                            current_app=current_app)
