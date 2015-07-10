"""
Some extra URL patterns that are included at the top level.
"""

from django.conf.urls import include, url

from .views import empty_view

urlpatterns = [
    url(r'^e-places/([0-9]+)/$', empty_view, name='extra-places'),
    url(r'^e-people/(?P<name>\w+)/$', empty_view, name="extra-people"),
    url('', include('urlpatterns_reverse.included_urls2')),
    url(r'^prefix/(?P<prefix>\w+)/', include('urlpatterns_reverse.included_urls2')),
]
