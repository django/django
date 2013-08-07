from django.conf.urls import patterns, url
from django.contrib.auth import context_processors
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.urls import urlpatterns
from django.contrib.auth.views import password_reset, login
from django.contrib.auth.decorators import login_required
from django.contrib.messages.api import info
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render_to_response
from django.template import Template, RequestContext
from django.views.decorators.cache import never_cache

class CustomRequestAuthenticationForm(AuthenticationForm):
    def __init__(self, request, *args, **kwargs):
        assert isinstance(request, HttpRequest)
        super(CustomRequestAuthenticationForm, self).__init__(request, *args, **kwargs)

@never_cache
def remote_user_auth_view(request):
    "Dummy view for remote user tests"
    t = Template("Username is {{ user }}.")
    c = RequestContext(request, {})
    return HttpResponse(t.render(c))

def auth_processor_no_attr_access(request):
    r1 = render_to_response('context_processors/auth_attrs_no_access.html',
        RequestContext(request, {}, processors=[context_processors.auth]))
    # *After* rendering, we check whether the session was accessed
    return render_to_response('context_processors/auth_attrs_test_access.html',
        {'session_accessed':request.session.accessed})

def auth_processor_attr_access(request):
    r1 = render_to_response('context_processors/auth_attrs_access.html',
        RequestContext(request, {}, processors=[context_processors.auth]))
    return render_to_response('context_processors/auth_attrs_test_access.html',
        {'session_accessed':request.session.accessed})

def auth_processor_user(request):
    return render_to_response('context_processors/auth_attrs_user.html',
        RequestContext(request, {}, processors=[context_processors.auth]))

def auth_processor_perms(request):
    return render_to_response('context_processors/auth_attrs_perms.html',
        RequestContext(request, {}, processors=[context_processors.auth]))

def auth_processor_perm_in_perms(request):
    return render_to_response('context_processors/auth_attrs_perm_in_perms.html',
        RequestContext(request, {}, processors=[context_processors.auth]))

def auth_processor_messages(request):
    info(request, "Message 1")
    return render_to_response('context_processors/auth_attrs_messages.html',
         RequestContext(request, {}, processors=[context_processors.auth]))

def userpage(request):
    pass

def custom_request_auth_login(request):
    return login(request, authentication_form=CustomRequestAuthenticationForm)

# special urls for auth test cases
urlpatterns = urlpatterns + patterns('',
    (r'^logout/custom_query/$', 'django.contrib.auth.views.logout', dict(redirect_field_name='follow')),
    (r'^logout/next_page/$', 'django.contrib.auth.views.logout', dict(next_page='/somewhere/')),
    (r'^logout/next_page/named/$', 'django.contrib.auth.views.logout', dict(next_page='password_reset')),
    (r'^remote_user/$', remote_user_auth_view),
    (r'^password_reset_from_email/$', 'django.contrib.auth.views.password_reset', dict(from_email='staffmember@example.com')),
    (r'^password_reset/custom_redirect/$', 'django.contrib.auth.views.password_reset', dict(post_reset_redirect='/custom/')),
    (r'^password_reset/custom_redirect/named/$', 'django.contrib.auth.views.password_reset', dict(post_reset_redirect='password_reset')),
    (r'^reset/custom/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        'django.contrib.auth.views.password_reset_confirm',
        dict(post_reset_redirect='/custom/')),
    (r'^reset/custom/named/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        'django.contrib.auth.views.password_reset_confirm',
        dict(post_reset_redirect='password_reset')),
    (r'^password_change/custom/$', 'django.contrib.auth.views.password_change', dict(post_change_redirect='/custom/')),
    (r'^password_change/custom/named/$', 'django.contrib.auth.views.password_change', dict(post_change_redirect='password_reset')),
    (r'^admin_password_reset/$', 'django.contrib.auth.views.password_reset', dict(is_admin_site=True)),
    (r'^login_required/$', login_required(password_reset)),
    (r'^login_required_login_url/$', login_required(password_reset, login_url='/somewhere/')),

    (r'^auth_processor_no_attr_access/$', auth_processor_no_attr_access),
    (r'^auth_processor_attr_access/$', auth_processor_attr_access),
    (r'^auth_processor_user/$', auth_processor_user),
    (r'^auth_processor_perms/$', auth_processor_perms),
    (r'^auth_processor_perm_in_perms/$', auth_processor_perm_in_perms),
    (r'^auth_processor_messages/$', auth_processor_messages),
    (r'^custom_request_auth_login/$', custom_request_auth_login),
    url(r'^userpage/(.+)/$', userpage, name="userpage"),
)
