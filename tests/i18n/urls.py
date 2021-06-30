from mango.conf.urls.i18n import i18n_patterns
from mango.http import HttpResponse, StreamingHttpResponse
from mango.urls import path
from mango.utils.translation import gettext_lazy as _

urlpatterns = i18n_patterns(
    path('simple/', lambda r: HttpResponse()),
    path('streaming/', lambda r: StreamingHttpResponse([_('Yes'), '/', _('No')])),
)
