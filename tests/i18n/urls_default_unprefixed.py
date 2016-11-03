from django.conf.urls import url, include
from django.conf.urls.i18n import i18n_patterns
from django.http import HttpResponse, Http404
from django.utils.translation import ugettext_lazy as _


def raise_404(request, **kwargs):
    raise Http404()


raising_404_2_groups_pattern = url(r'^(?P<group1>.+)/(?P<group2>.+)/$', raise_404)

extra_patterns = [
    raising_404_2_groups_pattern
]

urlpatterns = i18n_patterns(
    url(r'^(?P<arg>[\w-]+)-page', lambda request, **arg: HttpResponse(_("Yes"))),
    url(r'^simple/$', lambda r: HttpResponse(_("Yes"))),
    url(r'^prefix/', include(extra_patterns)),
    raising_404_2_groups_pattern,
    prefix_default_language=False,
)
