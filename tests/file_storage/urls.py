from django.conf.urls import patterns, url
from django.http import HttpResponse


urlpatterns = patterns('',
    url(r'^$', lambda req: HttpResponse('example view')),
)
