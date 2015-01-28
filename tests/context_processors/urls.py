from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^request_attrs/$', views.request_processor),
    url(r'^debug/$', views.debug_processor),
]
