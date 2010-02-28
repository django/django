from django.conf.urls.defaults import *

urlpatterns = patterns('regressiontests.debug.views',
    url(r'view_exception/(?P<n>\d+)/$', 'view_exception', name='view_exception'),
)
