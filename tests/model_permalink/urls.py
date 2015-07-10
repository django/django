from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^guitarists/(\w{1,50})/$', views.empty_view, name='guitarist_detail'),
]
