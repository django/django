from django.conf.urls import patterns

urlpatterns = patterns('',
    (r'^noslash$', 'view'),
    (r'^slash/$', 'view'),
    (r'^needsquoting#/$', 'view'),
)
