from django.conf.urls.defaults import *
from feeds import TestGeoRSS1, TestGeoRSS2, TestGeoAtom1, TestGeoAtom2, TestW3CGeo1, TestW3CGeo2, TestW3CGeo3

feed_dict = {
    'rss1' : TestGeoRSS1,
    'rss2' : TestGeoRSS2,
    'atom1' : TestGeoAtom1,
    'atom2' : TestGeoAtom2,
    'w3cgeo1' : TestW3CGeo1,
    'w3cgeo2' : TestW3CGeo2,
    'w3cgeo3' : TestW3CGeo3,
}

urlpatterns = patterns('',
    (r'^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.feed', {'feed_dict': feed_dict})
)
