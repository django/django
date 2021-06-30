from mango.contrib.flatpages.sitemaps import FlatPageSitemap
from mango.contrib.sitemaps import views
from mango.urls import include, path

urlpatterns = [
    path(
        'flatpages/sitemap.xml', views.sitemap,
        {'sitemaps': {'flatpages': FlatPageSitemap}},
        name='mango.contrib.sitemaps.views.sitemap'),

    path('flatpage_root/', include('mango.contrib.flatpages.urls')),
    path('accounts/', include('mango.contrib.auth.urls')),
]
