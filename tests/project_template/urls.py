from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^empty/$', views.empty_view),
]
