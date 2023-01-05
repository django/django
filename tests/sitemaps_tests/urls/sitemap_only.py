from django.contrib.sitemaps import views
from django.urls import path

urlpatterns = [
    path(
        "sitemap-without-entries/sitemap.xml",
        views.sitemap,
        {"sitemaps": {}},
        name="django.contrib.sitemaps.views.sitemap",
    ),
]
