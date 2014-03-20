from django.conf.urls import patterns, url

from .views import empty_view


urlpatterns = patterns('',
    url(r'^inner-no-kwargs/(\d+)/', empty_view, name="inner-no-kwargs")
)
