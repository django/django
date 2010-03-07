from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^middleware/customurlconf/noslash$', 'view'),
    (r'^middleware/customurlconf/slash/$', 'view'),
    (r'^middleware/customurlconf/needsquoting#/$', 'view'),
)
