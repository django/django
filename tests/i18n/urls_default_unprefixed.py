from django.conf.urls import url
from django.conf.urls.i18n import i18n_patterns
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

urlpatterns = i18n_patterns(
    url(r'^(?P<arg>[\w-]+)-page', lambda request, **arg: HttpResponse(_("Yes"))),
    url(r'^simple/$', lambda r: HttpResponse(_("Yes"))),
    url(r'^(.+)/(.+)/$', lambda *args: HttpResponse()),
    prefix_default_language=False,
)
