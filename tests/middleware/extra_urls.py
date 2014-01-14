from django.conf.urls import patterns

urlpatterns = patterns('',
    (r'^customurlconf/noslash$', 'view'),
    (r'^customurlconf/slash/$', 'view'),
    (r'^customurlconf/needsquoting#/$', 'view'),
)
