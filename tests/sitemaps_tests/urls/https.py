from thibaud.contrib.sitemaps import views
from thibaud.urls import path

from .http import SimpleSitemap


class HTTPSSitemap(SimpleSitemap):
    protocol = "https"


secure_sitemaps = {
    "simple": HTTPSSitemap,
}

urlpatterns = [
    path("secure/index.xml", views.index, {"sitemaps": secure_sitemaps}),
    path(
        "secure/sitemap-<section>.xml",
        views.sitemap,
        {"sitemaps": secure_sitemaps},
        name="thibaud.contrib.sitemaps.views.sitemap",
    ),
]
