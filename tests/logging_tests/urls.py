from __future__ import unicode_literals

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^innocent/$', views.innocent),
    url(r'^suspicious/$', views.suspicious),
    url(r'^suspicious_spec/$', views.suspicious_spec),
    url(r'^internal_server_error/$', views.internal_server_error),
    url(r'^uncaught_exception/$', views.uncaught_exception),
    url(r'^permission_denied/$', views.permission_denied),
    url(r'^multi_part_parser_error/$', views.multi_part_parser_error),
    url(r'^does_not_exist_raised/$', views.does_not_exist_raised),
]
