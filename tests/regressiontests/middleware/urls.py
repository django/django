from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^noslash$', 'view'),
    (r'^slash/$', 'view'),
    (r'^needsquoting#/$', 'view'),
)
