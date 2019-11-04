from django.conf.urls.i18n import i18n_patterns
from django.http import HttpResponse, StreamingHttpResponse
from django.urls import path
from django.utils.translation import gettext_lazy as _

urlpatterns = i18n_patterns(
    path('simple/', lambda r: HttpResponse()),
    path('streaming/', lambda r: StreamingHttpResponse([_('Yes'), '/', _('No')])),
)
