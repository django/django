from __future__ import unicode_literals

from django.conf.urls.i18n import i18n_patterns
from django.http import HttpResponse, StreamingHttpResponse
from django.utils.translation import ugettext_lazy as _

urlpatterns = i18n_patterns('',
    (r'^simple/$', lambda r: HttpResponse()),
    (r'^streaming/$', lambda r: StreamingHttpResponse([_("Yes"), "/", _("No")])),
)
