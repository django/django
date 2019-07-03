from django.contrib import admin
from django.contrib.auth import views
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.urls import urlpatterns as auth_urlpatterns
from django.contrib.messages.api import info
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template import RequestContext, Template
from django.urls import path, re_path, reverse_lazy
from django.views.decorators.cache import never_cache
from django.views.i18n import set_language


class CustomRequestAuthenticationForm(AuthenticationForm):
    def __init__(self, request, *args, **kwargs):
        assert isinstance(request, HttpRequest)
        super().__init__(request, *args, **kwargs)


@never_cache
def remote_user_auth_view(request):
    "Dummy view for remote user tests"
    t = Template("Username is {{ user }}.")
    c = RequestContext(request, {})
    return HttpResponse(t.render(c))


def auth_processor_no_attr_access(request):
    render(request, 'context_processors/auth_attrs_no_access.html')
    # *After* rendering, we check whether the session was accessed
    return render(request,
                  'context_processors/auth_attrs_test_access.html',
                  {'session_accessed': request.session.accessed})


def auth_processor_attr_access(request):
    render(request, 'context_processors/auth_attrs_access.html')
    return render(request,
                  'context_processors/auth_attrs_test_access.html',
                  {'session_accessed': request.session.accessed})


def auth_processor_user(request):
    return render(request, 'context_processors/auth_attrs_user.html')


def auth_processor_perms(request):
    return render(request, 'context_processors/auth_attrs_perms.html')


def auth_processor_perm_in_perms(request):
    return render(request, 'context_processors/auth_attrs_perm_in_perms.html')


def auth_processor_messages(request):
    info(request, "Message 1")
    return render(request, 'context_processors/auth_attrs_messages.html')


def userpage(request):
    pass


@permission_required('unknown.permission')
def permission_required_redirect(request):
    pass


@permission_required('unknown.permission', raise_exception=True)
def permission_required_exception(request):
    pass


@login_required
@permission_required('unknown.permission', raise_exception=True)
def login_and_permission_required_exception(request):
    pass


uid_token = r'(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})'

# special urls for auth test cases
urlpatterns = auth_urlpatterns + [
    path('logout/custom_query/', views.LogoutView.as_view(redirect_field_name='follow')),
    path('logout/next_page/', views.LogoutView.as_view(next_page='/somewhere/')),
    path('logout/next_page/named/', views.LogoutView.as_view(next_page='password_reset')),
    path('logout/allowed_hosts/', views.LogoutView.as_view(success_url_allowed_hosts={'otherserver'})),
    path('remote_user/', remote_user_auth_view),

    path('password_reset_from_email/', views.PasswordResetView.as_view(from_email='staffmember@example.com')),
    path(
        'password_reset_extra_email_context/',
        views.PasswordResetView.as_view(
            extra_email_context={'greeting': 'Hello!', 'domain': 'custom.example.com'},
        ),
    ),
    path(
        'password_reset/custom_redirect/',
        views.PasswordResetView.as_view(success_url='/custom/')),
    path(
        'password_reset/custom_redirect/named/',
        views.PasswordResetView.as_view(success_url=reverse_lazy('password_reset'))),
    path(
        'password_reset/html_email_template/',
        views.PasswordResetView.as_view(
            html_email_template_name='registration/html_password_reset_email.html'
        )),
    re_path(
        '^reset/custom/{}/$'.format(uid_token),
        views.PasswordResetConfirmView.as_view(success_url='/custom/'),
    ),
    re_path(
        '^reset/custom/named/{}/$'.format(uid_token),
        views.PasswordResetConfirmView.as_view(success_url=reverse_lazy('password_reset')),
    ),
    re_path(
        '^reset/custom/token/{}/$'.format(uid_token),
        views.PasswordResetConfirmView.as_view(reset_url_token='set-passwordcustom'),
    ),
    re_path(
        '^reset/post_reset_login/{}/$'.format(uid_token),
        views.PasswordResetConfirmView.as_view(post_reset_login=True),
    ),
    re_path(
        '^reset/post_reset_login_custom_backend/{}/$'.format(uid_token),
        views.PasswordResetConfirmView.as_view(
            post_reset_login=True,
            post_reset_login_backend='django.contrib.auth.backends.AllowAllUsersModelBackend',
        ),
    ),
    path('password_change/custom/',
         views.PasswordChangeView.as_view(success_url='/custom/')),
    path('password_change/custom/named/',
         views.PasswordChangeView.as_view(success_url=reverse_lazy('password_reset'))),
    path('login_required/', login_required(views.PasswordResetView.as_view())),
    path('login_required_login_url/', login_required(views.PasswordResetView.as_view(), login_url='/somewhere/')),

    path('auth_processor_no_attr_access/', auth_processor_no_attr_access),
    path('auth_processor_attr_access/', auth_processor_attr_access),
    path('auth_processor_user/', auth_processor_user),
    path('auth_processor_perms/', auth_processor_perms),
    path('auth_processor_perm_in_perms/', auth_processor_perm_in_perms),
    path('auth_processor_messages/', auth_processor_messages),
    path(
        'custom_request_auth_login/',
        views.LoginView.as_view(authentication_form=CustomRequestAuthenticationForm)),
    re_path('^userpage/(.+)/$', userpage, name='userpage'),
    path('login/redirect_authenticated_user_default/', views.LoginView.as_view()),
    path('login/redirect_authenticated_user/',
         views.LoginView.as_view(redirect_authenticated_user=True)),
    path('login/allowed_hosts/',
         views.LoginView.as_view(success_url_allowed_hosts={'otherserver'})),

    path('permission_required_redirect/', permission_required_redirect),
    path('permission_required_exception/', permission_required_exception),
    path('login_and_permission_required_exception/', login_and_permission_required_exception),

    path('setlang/', set_language, name='set_language'),
    # This line is only required to render the password reset with is_admin=True
    path('admin/', admin.site.urls),
]
