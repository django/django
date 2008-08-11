from django.core.exceptions import ObjectDoesNotExist
from django.contrib.syndication import feeds
from django.utils.feedgenerator import Atom1Feed

class ComplexFeed(feeds.Feed):
    def get_object(self, bits):
        if len(bits) != 1:
            raise ObjectDoesNotExist
        return None

class TestRssFeed(feeds.Feed):
    link = "/blog/"
    title = 'My blog'
    
    def items(self):
        from models import Entry
        return Entry.objects.all()
        
    def item_link(self, item):
        return "/blog/%s/" % item.pk

class TestAtomFeed(TestRssFeed):
    feed_type = Atom1Feed
