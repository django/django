from django.conf.urls import url

urlpatterns = [
    url(r'^noslash$', 'middleware.views.empty_view'),
    url(r'^slash/$', 'middleware.views.empty_view'),
    url(r'^needsquoting#/$', 'middleware.views.empty_view'),
]
