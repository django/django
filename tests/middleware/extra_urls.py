from django.conf.urls import url

urlpatterns = [
    url(r'^customurlconf/noslash$', 'view'),
    url(r'^customurlconf/slash/$', 'view'),
    url(r'^customurlconf/needsquoting#/$', 'view'),
]
