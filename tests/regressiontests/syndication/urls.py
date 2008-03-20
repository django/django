from django.conf.urls.defaults import patterns
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.syndication import feeds


class ComplexFeed(feeds.Feed):
    def get_object(self, bits):
        if len(bits) != 1:
            raise ObjectDoesNotExist
        return None


urlpatterns = patterns('',
    (r'^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.feed', {
        'feed_dict': dict(
            complex = ComplexFeed,
        )}),
)
