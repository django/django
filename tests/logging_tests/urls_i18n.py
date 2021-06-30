from mango.conf.urls.i18n import i18n_patterns
from mango.http import HttpResponse
from mango.urls import path

urlpatterns = i18n_patterns(
    path('exists/', lambda r: HttpResponse()),
)
