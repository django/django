from django.conf.urls.defaults import *
from views import empty_view

urlpatterns = patterns('',
    url(r'^$', empty_view, name="named-url1"),
    url(r'^extra/(?P<extra>\w+)/$', empty_view, name="named-url2"),
    url(r'^(?P<one>\d+)|(?P<two>\d+)/$', empty_view),
    (r'^included/', include('regressiontests.urlpatterns_reverse.included_named_urls')),
)
