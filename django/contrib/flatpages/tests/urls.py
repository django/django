from django.conf.urls import include, url
from django.contrib.flatpages.sitemaps import FlatPageSitemap
from django.contrib.sitemaps import views

# special urls for flatpage test cases
urlpatterns = [
    url(r'^flatpages/sitemap\.xml$', views.sitemap,
        {'sitemaps': {'flatpages': FlatPageSitemap}},
        name='django.contrib.sitemaps.views.sitemap'),

    url(r'^flatpage_root', include('django.contrib.flatpages.urls')),
    url(r'^accounts/', include('django.contrib.auth.urls')),
]
