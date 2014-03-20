# Used by the ErrorHandlerResolutionTests test case.

from django.conf.urls import patterns

urlpatterns = patterns('')

handler400 = 'urlpatterns_reverse.views.empty_view'
handler404 = 'urlpatterns_reverse.views.empty_view'
handler500 = 'urlpatterns_reverse.views.empty_view'
