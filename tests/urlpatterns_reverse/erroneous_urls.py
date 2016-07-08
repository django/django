from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'(regex_error/$', views.empty_view),
]
