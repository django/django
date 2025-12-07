from django.conf.urls.i18n import i18n_patterns
from django.http import HttpResponse
from django.urls import path

urlpatterns = i18n_patterns(
    path("exists/", lambda r: HttpResponse()),
)
