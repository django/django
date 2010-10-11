from django.contrib.syndication import views
from django.core.exceptions import ObjectDoesNotExist
import warnings

# This is part of the deprecated API
from django.contrib.syndication.views import FeedDoesNotExist, add_domain

class Feed(views.Feed):
    """Provided for backwards compatibility."""
    def __init__(self, slug, request):
        warnings.warn('The syndication feeds.Feed class is deprecated. Please '
                      'use the new class based view API.',
                      category=DeprecationWarning)

        self.slug = slug
        self.request = request
        self.feed_url = getattr(self, 'feed_url', None) or request.path
        self.title_template = self.title_template or ('feeds/%s_title.html' % slug)
        self.description_template = self.description_template or ('feeds/%s_description.html' % slug)

    def get_object(self, bits):
        return None

    def get_feed(self, url=None):
        """
        Returns a feedgenerator.DefaultFeed object, fully populated, for
        this feed. Raises FeedDoesNotExist for invalid parameters.
        """
        if url:
            bits = url.split('/')
        else:
            bits = []
        try:
            obj = self.get_object(bits)
        except ObjectDoesNotExist:
            raise FeedDoesNotExist
        return super(Feed, self).get_feed(obj, self.request)

