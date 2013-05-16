from django.conf.urls import patterns
from django.http import HttpResponse

urlpatterns = patterns('',
    (r'^$', lambda request: HttpResponse('root is here')),
)
