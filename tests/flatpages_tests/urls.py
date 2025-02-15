from thibaud.contrib.flatpages.sitemaps import FlatPageSitemap
from thibaud.contrib.sitemaps import views
from thibaud.urls import include, path

urlpatterns = [
    path(
        "flatpages/sitemap.xml",
        views.sitemap,
        {"sitemaps": {"flatpages": FlatPageSitemap}},
        name="thibaud.contrib.sitemaps.views.sitemap",
    ),
    path("flatpage_root/", include("thibaud.contrib.flatpages.urls")),
    path("accounts/", include("thibaud.contrib.auth.urls")),
]
