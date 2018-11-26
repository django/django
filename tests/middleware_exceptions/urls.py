from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^middleware_exceptions/view/$', views.normal_view),
    url(r'^middleware_exceptions/error/$', views.server_error),
    url(r'^middleware_exceptions/permission_denied/$', views.permission_denied),
    url(r'^middleware_exceptions/exception_in_render/$', views.exception_in_render),
    url(r'^middleware_exceptions/template_response/$', views.template_response),
]
