from django.urls import path

from . import views

urlpatterns = [
    path('middleware_exceptions/view/', views.normal_view),
    path('middleware_exceptions/error/', views.server_error),
    path('middleware_exceptions/permission_denied/', views.permission_denied),
    path('middleware_exceptions/exception_in_render/', views.exception_in_render),
    path('middleware_exceptions/template_response/', views.template_response),
]
