from django.conf.urls import url
from django.contrib.staticfiles import views

urlpatterns = [
    url(r'^static/(?P<path>.*)$', views.serve),
]
