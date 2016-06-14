from django.conf.urls import url

from . import views

urlpatterns = [
    url('^404-with-session-modify/$', views.session_modify_and_http404, name='http404-with-session-modify'),
]
