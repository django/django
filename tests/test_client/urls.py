from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path('upload_view/', views.upload_view, name='upload_view'),
    path('get_view/', views.get_view, name='get_view'),
    path('post_view/', views.post_view),
    path('put_view/', views.put_view),
    path('trace_view/', views.trace_view),
    path('header_view/', views.view_with_header),
    path('raw_post_view/', views.raw_post_view),
    path('redirect_view/', views.redirect_view),
    path('redirect_view_307/', views.method_saving_307_redirect_view),
    path('redirect_view_308/', views.method_saving_308_redirect_view),
    path('secure_view/', views.view_with_secure),
    path('permanent_redirect_view/', RedirectView.as_view(url='/get_view/', permanent=True)),
    path('temporary_redirect_view/', RedirectView.as_view(url='/get_view/', permanent=False)),
    path('http_redirect_view/', RedirectView.as_view(url='/secure_view/')),
    path('https_redirect_view/', RedirectView.as_view(url='https://testserver/secure_view/')),
    path('double_redirect_view/', views.double_redirect_view),
    path('bad_view/', views.bad_view),
    path('form_view/', views.form_view),
    path('form_view_with_template/', views.form_view_with_template),
    path('formset_view/', views.formset_view),
    path('json_view/', views.json_view),
    path('login_protected_view/', views.login_protected_view),
    path('login_protected_method_view/', views.login_protected_method_view),
    path('login_protected_view_custom_redirect/', views.login_protected_view_changed_redirect),
    path('permission_protected_view/', views.permission_protected_view),
    path('permission_protected_view_exception/', views.permission_protected_view_exception),
    path('permission_protected_method_view/', views.permission_protected_method_view),
    path('session_view/', views.session_view),
    path('broken_view/', views.broken_view),
    path('mail_sending_view/', views.mail_sending_view),
    path('mass_mail_sending_view/', views.mass_mail_sending_view),
    path('nesting_exception_view/', views.nesting_exception_view),
    path('django_project_redirect/', views.django_project_redirect),
    path('two_arg_exception/', views.two_arg_exception),

    path('accounts/', RedirectView.as_view(url='login/')),
    path('accounts/no_trailing_slash', RedirectView.as_view(url='login/')),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html')),
    path('accounts/logout/', auth_views.LogoutView.as_view()),
]
