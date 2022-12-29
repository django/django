from functools import partial
from pathlib import Path

from django.conf.urls.i18n import i18n_patterns
from django.urls import include, path, re_path
from django.utils.translation import gettext_lazy as _
from django.views import defaults, i18n, static

from . import views

base_dir = Path(__file__).parent
media_dir = base_dir / "media"
locale_dir = base_dir / "locale"

urlpatterns = [
    path("", views.index_page),
    # Default views
    path("nonexistent_url/", partial(defaults.page_not_found, exception=None)),
    path("server_error/", defaults.server_error),
    # a view that raises an exception for the debug view
    path("raises/", views.raises),
    path("raises400/", views.raises400),
    path("raises400_bad_request/", views.raises400_bad_request),
    path("raises403/", views.raises403),
    path("raises404/", views.raises404),
    path("raises500/", views.raises500),
    path("custom_reporter_class_view/", views.custom_reporter_class_view),
    path("technical404/", views.technical404, name="my404"),
    path("classbased404/", views.Http404View.as_view()),
    path("classbased500/", views.Raises500View.as_view()),
    # i18n views
    path("i18n/", include("django.conf.urls.i18n")),
    path("jsi18n/", i18n.JavaScriptCatalog.as_view(packages=["view_tests"])),
    path("jsi18n_no_packages/", i18n.JavaScriptCatalog.as_view()),
    path("jsi18n/app1/", i18n.JavaScriptCatalog.as_view(packages=["view_tests.app1"])),
    path("jsi18n/app2/", i18n.JavaScriptCatalog.as_view(packages=["view_tests.app2"])),
    path("jsi18n/app5/", i18n.JavaScriptCatalog.as_view(packages=["view_tests.app5"])),
    path(
        "jsi18n_english_translation/",
        i18n.JavaScriptCatalog.as_view(packages=["view_tests.app0"]),
    ),
    path(
        "jsi18n_multi_packages1/",
        i18n.JavaScriptCatalog.as_view(packages=["view_tests.app1", "view_tests.app2"]),
    ),
    path(
        "jsi18n_multi_packages2/",
        i18n.JavaScriptCatalog.as_view(packages=["view_tests.app3", "view_tests.app4"]),
    ),
    path(
        "jsi18n_admin/",
        i18n.JavaScriptCatalog.as_view(packages=["django.contrib.admin", "view_tests"]),
    ),
    path("jsi18n_template/", views.jsi18n),
    path("jsi18n_multi_catalogs/", views.jsi18n_multi_catalogs),
    path("jsoni18n/", i18n.JSONCatalog.as_view(packages=["view_tests"])),
    # Static views
    re_path(
        r"^site_media/(?P<path>.*)$",
        static.serve,
        {"document_root": media_dir, "show_indexes": True},
    ),
]

urlpatterns += i18n_patterns(
    re_path(_(r"^translated/$"), views.index_page, name="i18n_prefixed"),
)

urlpatterns += [
    path(
        "safestring_exception/",
        views.safestring_in_template_exception,
        name="safestring_exception",
    ),
    path("template_exception/", views.template_exception, name="template_exception"),
    path(
        "raises_template_does_not_exist/<path:path>",
        views.raises_template_does_not_exist,
        name="raises_template_does_not_exist",
    ),
    path("render_no_template/", views.render_no_template, name="render_no_template"),
    re_path(
        r"^test-setlang/(?P<parameter>[^/]+)/$",
        views.with_parameter,
        name="with_parameter",
    ),
    # Patterns to test the technical 404.
    re_path(r"^regex-post/(?P<pk>[0-9]+)/$", views.index_page, name="regex-post"),
    path("path-post/<int:pk>/", views.index_page, name="path-post"),
]
