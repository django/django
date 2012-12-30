from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.http import HttpResponse, StreamingHttpResponse

urlpatterns = patterns('',
    url(r'^regular/$', lambda request: HttpResponse(b"regular content")),
    url(r'^streaming/$', lambda request: StreamingHttpResponse([b"streaming", b" ", b"content"])),
)
