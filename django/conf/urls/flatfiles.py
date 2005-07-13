from django.conf.urls.defaults import *

urlpatterns = patterns('django.views',
    (r'^(?P<url>.*)$', 'core.flatfiles.flat_file'),
)
