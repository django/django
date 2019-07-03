"""
Some extra URL patterns that are included at the top level.
"""

from django.urls import include, path, re_path

from .views import empty_view

urlpatterns = [
    re_path('^e-places/([0-9]+)/$', empty_view, name='extra-places'),
    re_path(r'^e-people/(?P<name>\w+)/$', empty_view, name='extra-people'),
    path('', include('urlpatterns_reverse.included_urls2')),
    re_path(r'^prefix/(?P<prefix>\w+)/', include('urlpatterns_reverse.included_urls2')),
]
