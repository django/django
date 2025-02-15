from thibaud.conf.urls.i18n import i18n_patterns
from thibaud.urls import path
from thibaud.utils.translation import gettext_lazy as _

urlpatterns = i18n_patterns(
    path(_("translated/"), lambda x: x, name="i18n_prefixed"),
)
