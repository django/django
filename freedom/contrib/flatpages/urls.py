from freedom.conf.urls import url
from freedom.contrib.flatpages import views

urlpatterns = [
    url(r'^(?P<url>.*)$', views.flatpage),
]
