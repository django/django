# Used by the ErrorHandlerResolutionTests test case.

from __future__ import absolute_import

from django.conf.urls import patterns

from .views import empty_view


urlpatterns = patterns('')

handler400 = empty_view
handler404 = empty_view
handler500 = empty_view
