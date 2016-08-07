from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth import views
from django.contrib.auth.decorators import login_required

# special urls for deprecated function-based views
urlpatterns = [
    url(r'^login/$', views.login, name='login'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^password_change/$', views.password_change, name='password_change'),
    url(r'^password_change/done/$', views.password_change_done, name='password_change_done'),
    url(r'^password_reset/$', views.password_reset, name='password_reset'),
    url(r'^password_reset/done/$', views.password_reset_done, name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.password_reset_confirm, name='password_reset_confirm'),
    url(r'^reset/done/$', views.password_reset_complete, name='password_reset_complete'),

    url(r'^password_reset_from_email/$', views.password_reset, dict(from_email='staffmember@example.com')),
    url(r'^password_reset_extra_email_context/$', views.password_reset,
        dict(extra_email_context=dict(greeting='Hello!'))),
    url(r'^password_reset/custom_redirect/$', views.password_reset, dict(post_reset_redirect='/custom/')),
    url(r'^password_reset/custom_redirect/named/$', views.password_reset, dict(post_reset_redirect='password_reset')),
    url(r'^password_reset/html_email_template/$', views.password_reset,
        dict(html_email_template_name='registration/html_password_reset_email.html')),
    url(r'^reset/custom/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.password_reset_confirm,
        dict(post_reset_redirect='/custom/')),
    url(r'^reset/custom/named/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.password_reset_confirm,
        dict(post_reset_redirect='password_reset')),
    url(r'^password_change/custom/$', views.password_change, dict(post_change_redirect='/custom/')),
    url(r'^password_change/custom/named/$', views.password_change, dict(post_change_redirect='password_reset')),
    url(r'^login_required/$', login_required(views.password_reset)),
    url(r'^login_required_login_url/$', login_required(views.password_reset, login_url='/somewhere/')),

    # This line is only required to render the password reset with is_admin=True
    url(r'^admin/', admin.site.urls),
]
