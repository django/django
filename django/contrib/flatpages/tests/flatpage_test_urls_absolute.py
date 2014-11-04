from django.conf.urls import url
from django.contrib.flatpages import views

# special urls for flatpage test cases
urlpatterns = [
    url(r'^flatpage/$', views.flatpage, {'url': '/hard_coded_url/'}),
]

