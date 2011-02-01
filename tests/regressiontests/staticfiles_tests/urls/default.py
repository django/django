from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^static/(?P<path>.*)$', 'django.contrib.staticfiles.views.serve'),
)
