from django.conf.urls import include, url

from .views import empty_view

urlpatterns = [
    url(r'^normal/$', empty_view, name='inc-relative-normal-view'),
]
