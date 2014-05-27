from freedom.conf.urls import include, url
from freedom.conf.urls.i18n import i18n_patterns
from freedom.utils.translation import ugettext_lazy as _


urlpatterns = i18n_patterns(
    url(_(r'^account/'), include('i18n.patterns.urls.wrong_namespace', namespace='account')),
)
