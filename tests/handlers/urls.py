from django.conf.urls import url
from django.urls import path

from . import views

urlpatterns = [
    url(r'^regular/$', views.regular),
    path('no_response_fbv/', views.no_response),
    path('no_response_cbv/', views.NoResponse()),
    url(r'^streaming/$', views.streaming),
    url(r'^in_transaction/$', views.in_transaction),
    url(r'^not_in_transaction/$', views.not_in_transaction),
    url(r'^suspicious/$', views.suspicious),
    url(r'^malformed_post/$', views.malformed_post),
    url(r'^httpstatus_enum/$', views.httpstatus_enum),
]
