from mango.contrib.sitemaps import views
from mango.urls import path

from .http import simple_sitemaps

urlpatterns = [
    path(
        'simple/index.xml', views.index, {'sitemaps': simple_sitemaps},
        name='mango.contrib.sitemaps.views.index'),
]
