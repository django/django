from django.core import urlresolvers
from django.contrib.sitemaps import Sitemap

class GeoRSSSitemap(Sitemap):
    """
    A minimal hook to produce sitemaps for GeoRSS feeds.
    """
    def __init__(self, feed_dict, slug_dict=None):
        """
        This sitemap object initializes on a feed dictionary (as would be passed
        to `django.contrib.gis.views.feed`) and a slug dictionary.
        If the slug dictionary is not defined, then it's assumed the keys provide
        the URL parameter to the feed.  However, if you have a complex feed (e.g.,
        you override `get_object`, then you'll need to provide a slug dictionary.
        The slug dictionary should have the same keys as the feed dictionary, but
        each value in the slug dictionary should be a sequence of slugs that may
        be used for valid feeds.  For example, let's say we have a feed that
        returns objects for a specific ZIP code in our feed dictionary:

            feed_dict = {'zipcode' : ZipFeed}

        Then we would use a slug dictionary with a list of the zip code slugs
        corresponding to feeds you want listed in the sitemap:

            slug_dict = {'zipcode' : ['77002', '77054']}
        """
        # Setting up.
        self.feed_dict = feed_dict
        self.locations = []
        if slug_dict is None: slug_dict = {}
        # Getting the feed locations.
        for section in feed_dict.keys():
            if slug_dict.get(section, False):
                for slug in slug_dict[section]:
                    self.locations.append('%s/%s' % (section, slug))
            else:
                self.locations.append(section)

    def get_urls(self, page=1, site=None):
        """
        This method is overrridden so the appropriate `geo_format` attribute
        is placed on each URL element.
        """
        urls = Sitemap.get_urls(self, page=page, site=site)
        for url in urls: url['geo_format'] = 'georss'
        return urls

    def items(self):
        return self.locations

    def location(self, obj):
        return urlresolvers.reverse('django.contrib.gis.views.feed', args=(obj,))

