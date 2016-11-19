from django.conf.urls import url
from django.contrib.contenttypes import views

urlpatterns = [
    url(r'^shortcut/([0-9]+)/(.*)/$', views.shortcut),
]
