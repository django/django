from django.conf.urls import url

urlpatterns = [
    url(r'^noslash$', 'view'),
    url(r'^slash/$', 'view'),
    url(r'^needsquoting#/$', 'view'),
]
