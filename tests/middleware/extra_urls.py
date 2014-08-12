from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^customurlconf/noslash$', views.empty_view),
    url(r'^customurlconf/slash/$', views.empty_view),
    url(r'^customurlconf/needsquoting#/$', views.empty_view),
]
