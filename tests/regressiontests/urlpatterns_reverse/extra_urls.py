"""
Some extra URL patterns that are included at the top level.
"""

from django.conf.urls.defaults import *
from views import empty_view

urlpatterns = patterns('',
    url(r'^e-places/(\d+)/$', empty_view, name='extra-places'),
    url(r'^e-people/(?P<name>\w+)/$', empty_view, name="extra-people"),
)
