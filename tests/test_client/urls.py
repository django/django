from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    url(r'^upload_view/$', views.upload_view, name='upload_view'),
    url(r'^get_view/$', views.get_view, name='get_view'),
    url(r'^post_view/$', views.post_view),
    url(r'^put_view/$', views.put_view),
    url(r'^trace_view/$', views.trace_view),
    url(r'^header_view/$', views.view_with_header),
    url(r'^raw_post_view/$', views.raw_post_view),
    url(r'^redirect_view/$', views.redirect_view),
    url(r'^redirect_view_307/$', views.method_saving_307_redirect_view),
    url(r'^redirect_view_308/$', views.method_saving_308_redirect_view),
    url(r'^secure_view/$', views.view_with_secure),
    url(r'^permanent_redirect_view/$', RedirectView.as_view(url='/get_view/', permanent=True)),
    url(r'^temporary_redirect_view/$', RedirectView.as_view(url='/get_view/', permanent=False)),
    url(r'^http_redirect_view/$', RedirectView.as_view(url='/secure_view/')),
    url(r'^https_redirect_view/$', RedirectView.as_view(url='https://testserver/secure_view/')),
    url(r'^double_redirect_view/$', views.double_redirect_view),
    url(r'^bad_view/$', views.bad_view),
    url(r'^form_view/$', views.form_view),
    url(r'^form_view_with_template/$', views.form_view_with_template),
    url(r'^formset_view/$', views.formset_view),
    url(r'^json_view/$', views.json_view),
    url(r'^login_protected_view/$', views.login_protected_view),
    url(r'^login_protected_method_view/$', views.login_protected_method_view),
    url(r'^login_protected_view_custom_redirect/$', views.login_protected_view_changed_redirect),
    url(r'^permission_protected_view/$', views.permission_protected_view),
    url(r'^permission_protected_view_exception/$', views.permission_protected_view_exception),
    url(r'^permission_protected_method_view/$', views.permission_protected_method_view),
    url(r'^session_view/$', views.session_view),
    url(r'^broken_view/$', views.broken_view),
    url(r'^mail_sending_view/$', views.mail_sending_view),
    url(r'^mass_mail_sending_view/$', views.mass_mail_sending_view),
    url(r'^nesting_exception_view/$', views.nesting_exception_view),
    url(r'^django_project_redirect/$', views.django_project_redirect),
    url(r'^two_arg_exception/$', views.two_arg_exception),

    url(r'^accounts/$', RedirectView.as_view(url='login/')),
    url(r'^accounts/no_trailing_slash$', RedirectView.as_view(url='login/')),
    url(r'^accounts/login/$', auth_views.LoginView.as_view(template_name='login.html')),
    url(r'^accounts/logout/$', auth_views.LogoutView.as_view()),
]
