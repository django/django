from django.contrib.flatpages.sitemaps import FlatPageSitemap
from django.contrib.sitemaps import views
from django.urls import include, path

urlpatterns = [
    path(
        "flatpages/sitemap.xml",
        views.sitemap,
        {"sitemaps": {"flatpages": FlatPageSitemap}},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("flatpage_root/", include("django.contrib.flatpages.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
]
