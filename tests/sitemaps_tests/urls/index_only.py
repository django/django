from django.contrib.sitemaps import views
from django.urls import path

from .http import simple_sitemaps

urlpatterns = [
    path(
        "simple/index.xml",
        views.index,
        {"sitemaps": simple_sitemaps},
        name="django.contrib.sitemaps.views.index",
    ),
]
