from __future__ import unicode_literals

from django.conf.urls import url
from django.conf.urls.i18n import i18n_patterns
from django.http import HttpResponse

urlpatterns = i18n_patterns(
    url(r'^exists/$', lambda r: HttpResponse()),
)
