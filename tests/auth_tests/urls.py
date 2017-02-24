from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth import views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.urls import urlpatterns as auth_urlpatterns
from django.contrib.messages.api import info
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template import RequestContext, Template
from django.urls import reverse_lazy
from django.views.decorators.cache import never_cache


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


# special urls for auth test cases
urlpatterns = auth_urlpatterns + [
    url(r'^logout/custom_query/$', views.LogoutView.as_view(redirect_field_name='follow')),
    url(r'^logout/next_page/$', views.LogoutView.as_view(next_page='/somewhere/')),
    url(r'^logout/next_page/named/$', views.LogoutView.as_view(next_page='password_reset')),
    url(r'^logout/allowed_hosts/$', views.LogoutView.as_view(success_url_allowed_hosts={'otherserver'})),
    url(r'^remote_user/$', remote_user_auth_view),

    url(r'^password_reset_from_email/$',
        views.PasswordResetView.as_view(from_email='staffmember@example.com')),
    url(r'^password_reset_extra_email_context/$',
        views.PasswordResetView.as_view(extra_email_context=dict(greeting='Hello!'))),
    url(r'^password_reset/custom_redirect/$',
        views.PasswordResetView.as_view(success_url='/custom/')),
    url(r'^password_reset/custom_redirect/named/$',
        views.PasswordResetView.as_view(success_url=reverse_lazy('password_reset'))),
    url(r'^password_reset/html_email_template/$',
        views.PasswordResetView.as_view(
            html_email_template_name='registration/html_password_reset_email.html'
        )),
    url(r'^reset/custom/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.PasswordResetConfirmView.as_view(success_url='/custom/')),
    url(r'^reset/custom/named/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.PasswordResetConfirmView.as_view(success_url=reverse_lazy('password_reset'))),
    url(r'^reset/post_reset_login/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.PasswordResetConfirmView.as_view(post_reset_login=True)),
    url(r'^password_change/custom/$',
        views.PasswordChangeView.as_view(success_url='/custom/')),
    url(r'^password_change/custom/named/$',
        views.PasswordChangeView.as_view(success_url=reverse_lazy('password_reset'))),
    url(r'^login_required/$', login_required(views.PasswordResetView.as_view())),
    url(r'^login_required_login_url/$', login_required(views.PasswordResetView.as_view(), login_url='/somewhere/')),

    url(r'^auth_processor_no_attr_access/$', auth_processor_no_attr_access),
    url(r'^auth_processor_attr_access/$', auth_processor_attr_access),
    url(r'^auth_processor_user/$', auth_processor_user),
    url(r'^auth_processor_perms/$', auth_processor_perms),
    url(r'^auth_processor_perm_in_perms/$', auth_processor_perm_in_perms),
    url(r'^auth_processor_messages/$', auth_processor_messages),
    url(r'^custom_request_auth_login/$',
        views.LoginView.as_view(authentication_form=CustomRequestAuthenticationForm)),
    url(r'^userpage/(.+)/$', userpage, name="userpage"),
    url(r'^login/redirect_authenticated_user_default/$', views.LoginView.as_view()),
    url(r'^login/redirect_authenticated_user/$',
        views.LoginView.as_view(redirect_authenticated_user=True)),
    url(r'^login/allowed_hosts/$',
        views.LoginView.as_view(success_url_allowed_hosts={'otherserver'})),

    # This line is only required to render the password reset with is_admin=True
    url(r'^admin/', admin.site.urls),
]
