from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^noslash$', views.empty_view),
    url(r'^slash/$', views.empty_view),
    url(r'^needsquoting#/$', views.empty_view),
]
