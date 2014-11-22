from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^request_context_misuse/$', views.request_context_misuse),
]
