from django.conf.urls import url
from django.contrib.flatpages import views

urlpatterns = [
    url(r'^(?P<url>.*)$', views.flatpage, name='django.contrib.flatpages.views.flatpage'),
]
