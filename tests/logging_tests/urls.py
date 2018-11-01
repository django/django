from django.conf.urls import url
from django.urls import path

from . import views

urlpatterns = [
    url(r'^innocent/$', views.innocent),
    path('redirect/', views.redirect),
    url(r'^suspicious/$', views.suspicious),
    url(r'^suspicious_spec/$', views.suspicious_spec),
    path('internal_server_error/', views.internal_server_error),
    path('uncaught_exception/', views.uncaught_exception),
    path('permission_denied/', views.permission_denied),
    path('multi_part_parser_error/', views.multi_part_parser_error),
    path('does_not_exist_raised/', views.does_not_exist_raised),
]
