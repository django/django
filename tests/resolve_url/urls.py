from django.conf.urls import url
from django.contrib.auth import views

urlpatterns = [
    url(r'^accounts/logout/$', views.logout, name='logout'),
]
