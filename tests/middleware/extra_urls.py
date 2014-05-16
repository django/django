from django.conf.urls import url

urlpatterns = [
    url(r'^customurlconf/noslash$', 'middleware.views.empty_view'),
    url(r'^customurlconf/slash/$', 'middleware.views.empty_view'),
    url(r'^customurlconf/needsquoting#/$', 'middleware.views.empty_view'),
]
