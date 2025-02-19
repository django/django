# Used by the ErrorHandlerResolutionTests test case.

from .views import empty_view

urlpatterns = []

# RemovedInDjango61Warning: the handler<...> variables can be removed
handler400 = empty_view
handler403 = empty_view
handler404 = empty_view
handler500 = empty_view
error_handler = empty_view
