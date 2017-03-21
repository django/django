from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

view = TemplateView.as_view(template_name='dummy.html')

urlpatterns = [
    url(r'^not-prefixed/$', view, name='not-prefixed'),
    url(r'^not-prefixed-include/', include('i18n.patterns.urls.included')),
    url(_(r'^translated/$'), view, name='no-prefix-translated'),
    url(_(r'^translated/(?P<slug>[\w-]+)/$'), view, name='no-prefix-translated-slug'),
]

urlpatterns += i18n_patterns(
    url(r'^prefixed/$', view, name='prefixed'),
    url(r'^prefixed\.xml$', view, name='prefixed_xml'),
    url(_(r'^users/$'), view, name='users'),
    url(_(r'^account/'), include('i18n.patterns.urls.namespace', namespace='account')),
)
