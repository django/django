from __future__ import unicode_literals

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^regular/$', views.regular),
    url(r'^streaming/$', views.streaming),
    url(r'^in_transaction/$', views.in_transaction),
    url(r'^not_in_transaction/$', views.not_in_transaction),
    url(r'^suspicious/$', views.suspicious),
    url(r'^malformed_post/$', views.malformed_post),
]
