from thibaud.conf.urls.i18n import i18n_patterns
from thibaud.http import HttpResponse
from thibaud.urls import path

urlpatterns = i18n_patterns(
    path("exists/", lambda r: HttpResponse()),
)
