from django.conf.urls.defaults import *
from views import empty_view

urlpatterns = patterns('',
    url(r'^$', empty_view, name="named-url5"),
    url(r'^extra/(?P<extra>\w+)/$', empty_view, name="named-url6"),
    url(r'^(?P<one>\d+)|(?P<two>\d+)/$', empty_view),
)

