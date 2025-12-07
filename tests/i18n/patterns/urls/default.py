from django.conf.urls.i18n import i18n_patterns
from django.urls import include, path, re_path
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

view = TemplateView.as_view(template_name="dummy.html")

urlpatterns = [
    path("not-prefixed/", view, name="not-prefixed"),
    path("not-prefixed-include/", include("i18n.patterns.urls.included")),
    path(_("translated/"), view, name="no-prefix-translated"),
    re_path(_(r"^translated-regex/$"), view, name="no-prefix-translated-regex"),
    re_path(
        _(r"^translated/(?P<slug>[\w-]+)/$"),
        view,
        {"slug": "default-slug"},
        name="no-prefix-translated-slug",
    ),
]

urlpatterns += i18n_patterns(
    path("prefixed/", view, name="prefixed"),
    path("prefixed.xml", view, name="prefixed_xml"),
    re_path(
        _(r"^with-arguments/(?P<argument>[\w-]+)/(?:(?P<optional>[\w-]+).html)?$"),
        view,
        name="with-arguments",
    ),
    path(
        _("path-with-arguments/<str:argument>/"),
        view,
        name="path-with-arguments",
    ),
    re_path(_(r"^users/$"), view, name="users"),
    re_path(
        _(r"^account/"), include("i18n.patterns.urls.namespace", namespace="account")
    ),
)
