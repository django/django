from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.core.template import Context, loader, Template, TemplateDoesNotExist
from django.models.core import sites
from django.utils import feedgenerator
from django.conf.settings import LANGUAGE_CODE, SETTINGS_MODULE

def add_domain(domain, url):
    if not url.startswith('http://'):
        url = u'http://%s%s' % (domain, url)
    return url

class FeedDoesNotExist(ObjectDoesNotExist):
    pass

class Feed:
    item_pubdate = None
    item_enclosure_url = None
    feed_type = feedgenerator.DefaultFeed

    def __init__(self, slug):
        self.slug = slug

    def item_link(self, item):
        try:
            return item.get_absolute_url()
        except AttributeError:
            raise ImproperlyConfigured, "Give your %s class a get_absolute_url() method, or define an item_link() method in your Feed class." % item.__class__.__name__

    def __get_dynamic_attr(self, attname, obj):
        attr = getattr(self, attname)
        if callable(attr):
            try:
                return attr(obj)
            except TypeError:
                return attr()
        return attr

    def get_feed(self, url=None):
        """
        Returns a feedgenerator.DefaultFeed object, fully populated, for
        this feed. Raises FeedDoesNotExist for invalid parameters.
        """
        if url:
            try:
                obj = self.get_object(url.split('/'))
            except (AttributeError, ObjectDoesNotExist):
                raise FeedDoesNotExist
        else:
            obj = None

        current_site = sites.get_current()
        link = self.__get_dynamic_attr('link', obj)
        link = add_domain(current_site.domain, link)

        feed = self.feed_type(
            title = self.__get_dynamic_attr('title', obj),
            link = link,
            description = self.__get_dynamic_attr('description', obj),
            language = LANGUAGE_CODE.decode()
        )

        try:
            title_template = loader.get_template('feeds/%s_title' % self.slug)
        except TemplateDoesNotExist:
            title_template = Template('{{ obj }}')
        try:
            description_template = loader.get_template('feeds/%s_description' % self.slug)
        except TemplateDoesNotExist:
            description_template = Template('{{ obj }}')

        for item in self.__get_dynamic_attr('items', obj):
            link = add_domain(current_site.domain, self.__get_dynamic_attr('item_link', item))
            enc = None
            enc_url = self.__get_dynamic_attr('item_enclosure_url', item)
            if enc_url:
                enc = feedgenerator.Enclosure(
                    url = enc_url.decode('utf-8'),
                    length = str(self.__get_dynamic_attr('item_enclosure_length', item)).decode('utf-8'),
                    mime_type = self.__get_dynamic_attr('item_enclosure_mime_type', item).decode('utf-8'),
                )
            feed.add_item(
                title = title_template.render(Context({'obj': item, 'site': current_site})).decode('utf-8'),
                link = link,
                description = description_template.render(Context({'obj': item, 'site': current_site})).decode('utf-8'),
                unique_id = link,
                enclosure = enc,
                pubdate = self.__get_dynamic_attr('item_pubdate', item),
            )
        return feed
