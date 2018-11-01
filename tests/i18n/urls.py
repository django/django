from django.conf.urls import url
from django.conf.urls.i18n import i18n_patterns
from django.http import HttpResponse, StreamingHttpResponse
from django.utils.translation import gettext_lazy as _

urlpatterns = i18n_patterns(
    url(r'^simple/$', lambda r: HttpResponse()),
    url(r'^streaming/$', lambda r: StreamingHttpResponse([_("Yes"), "/", _("No")])),
)
