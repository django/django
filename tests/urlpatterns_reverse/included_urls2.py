"""
These URL patterns are included in two different ways in the main urls.py, with
an extra argument present in one case. Thus, there are two different ways for
each name to resolve and Django must distinguish the possibilities based on the
argument list.
"""

from django.conf.urls import url

from .views import empty_view

urlpatterns = [
    url(r'^part/(?P<value>\w+)/$', empty_view, name="part"),
    url(r'^part2/(?:(?P<value>\w+)/)?$', empty_view, name="part2"),
]
