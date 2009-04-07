from django.core.exceptions import ObjectDoesNotExist
from django.contrib.syndication import feeds
from django.utils.feedgenerator import Atom1Feed
from django.utils import tzinfo

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

class MyCustomAtom1Feed(Atom1Feed):
    """
    Test of a custom feed generator class.
    """    
    def root_attributes(self):
        attrs = super(MyCustomAtom1Feed, self).root_attributes()
        attrs[u'django'] = u'rocks'
        return attrs
        
    def add_root_elements(self, handler):
        super(MyCustomAtom1Feed, self).add_root_elements(handler)
        handler.addQuickElement(u'spam', u'eggs')
        
    def item_attributes(self, item):
        attrs = super(MyCustomAtom1Feed, self).item_attributes(item)
        attrs[u'bacon'] = u'yum'
        return attrs
        
    def add_item_elements(self, handler, item):
        super(MyCustomAtom1Feed, self).add_item_elements(handler, item)
        handler.addQuickElement(u'ministry', u'silly walks')
    
class TestCustomFeed(TestAtomFeed):
    feed_type = MyCustomAtom1Feed
    
class NaiveDatesFeed(TestAtomFeed):
    """
    A feed with naive (non-timezone-aware) dates.
    """
    def item_pubdate(self, item):
        return item.date
        
class TZAwareDatesFeed(TestAtomFeed):
    """
    A feed with timezone-aware dates.
    """
    def item_pubdate(self, item):
        # Provide a weird offset so that the test can know it's getting this
        # specific offset and not accidentally getting on from 
        # settings.TIME_ZONE.
        return item.date.replace(tzinfo=tzinfo.FixedOffset(42))