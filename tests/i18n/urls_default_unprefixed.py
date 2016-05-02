from django.conf.urls import url
from django.conf.urls.i18n import i18n_patterns
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _

urlpatterns = i18n_patterns(
    url(r'^simple/$', lambda r: HttpResponse(_("Yes"))),
    prefix_default_language=False,
)
