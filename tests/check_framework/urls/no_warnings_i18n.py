from django.conf.urls import url
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _

urlpatterns = i18n_patterns(
    url(_('translated/'), lambda x: x, name='i18n_prefixed'),
)
