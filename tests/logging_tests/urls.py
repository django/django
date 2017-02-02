from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^innocent/$', views.innocent),
    url(r'^suspicious/$', views.suspicious),
    url(r'^suspicious_spec/$', views.suspicious_spec),
]
