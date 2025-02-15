from thibaud.conf.urls.i18n import i18n_patterns
from thibaud.http import HttpResponse, StreamingHttpResponse
from thibaud.urls import path
from thibaud.utils.translation import gettext_lazy as _

urlpatterns = i18n_patterns(
    path("simple/", lambda r: HttpResponse()),
    path("streaming/", lambda r: StreamingHttpResponse([_("Yes"), "/", _("No")])),
)
