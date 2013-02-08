from __future__ import absolute_import

from django.conf.urls import patterns
from django.views.generic import RedirectView

from . import views


urlpatterns = patterns('',
    (r'^get_view/$', views.get_view),
    (r'^post_view/$', views.post_view),
    (r'^header_view/$', views.view_with_header),
    (r'^raw_post_view/$', views.raw_post_view),
    (r'^redirect_view/$', views.redirect_view),
    (r'^secure_view/$', views.view_with_secure),
    (r'^permanent_redirect_view/$', RedirectView.as_view(url='/test_client/get_view/')),
    (r'^temporary_redirect_view/$', RedirectView.as_view(url='/test_client/get_view/', permanent=False)),
    (r'^http_redirect_view/$', RedirectView.as_view(url='/test_client/secure_view/')),
    (r'^https_redirect_view/$', RedirectView.as_view(url='https://testserver/test_client/secure_view/')),
    (r'^double_redirect_view/$', views.double_redirect_view),
    (r'^bad_view/$', views.bad_view),
    (r'^form_view/$', views.form_view),
    (r'^form_view_with_template/$', views.form_view_with_template),
    (r'^formset_view/$', views.formset_view),
    (r'^login_protected_view/$', views.login_protected_view),
    (r'^login_protected_method_view/$', views.login_protected_method_view),
    (r'^login_protected_view_custom_redirect/$', views.login_protected_view_changed_redirect),
    (r'^permission_protected_view/$', views.permission_protected_view),
    (r'^permission_protected_view_exception/$', views.permission_protected_view_exception),
    (r'^permission_protected_method_view/$', views.permission_protected_method_view),
    (r'^session_view/$', views.session_view),
    (r'^broken_view/$', views.broken_view),
    (r'^mail_sending_view/$', views.mail_sending_view),
    (r'^mass_mail_sending_view/$', views.mass_mail_sending_view)
)
