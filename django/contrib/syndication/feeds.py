from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.template import Context, loader, Template, TemplateDoesNotExist
from django.contrib.sites.models import Site
from django.utils import feedgenerator
from django.conf import settings

def add_domain(domain, url):
    if not url.startswith('http://'):
        url = u'http://%s%s' % (domain, url)
    return url

class FeedDoesNotExist(ObjectDoesNotExist):
    pass

class Feed(object):
    item_pubdate = None
    item_enclosure_url = None
    feed_type = feedgenerator.DefaultFeed

    def __init__(self, slug, feed_url):
        self.slug = slug
        self.feed_url = feed_url

    def item_link(self, item):
        try:
            return item.get_absolute_url()
        except AttributeError:
            raise ImproperlyConfigured, "Give your %s class a get_absolute_url() method, or define an item_link() method in your Feed class." % item.__class__.__name__

    def __get_dynamic_attr(self, attname, obj, default=None):
        try:
            attr = getattr(self, attname)
        except AttributeError:
            return default
        if callable(attr):
            # Check func_code.co_argcount rather than try/excepting the
            # function and catching the TypeError, because something inside
            # the function may raise the TypeError. This technique is more
            # accurate.
            if hasattr(attr, 'func_code'):
                argcount = attr.func_code.co_argcount
            else:
                argcount = attr.__call__.func_code.co_argcount
            if argcount == 2: # one argument is 'self'
                return attr(obj)
            else:
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

        current_site = Site.objects.get_current()
        link = self.__get_dynamic_attr('link', obj)
        link = add_domain(current_site.domain, link)

        feed = self.feed_type(
            title = self.__get_dynamic_attr('title', obj),
            link = link,
            description = self.__get_dynamic_attr('description', obj),
            language = settings.LANGUAGE_CODE.decode(),
            feed_url = add_domain(current_site, self.feed_url),
            author_name = self.__get_dynamic_attr('author_name', obj),
            author_link = self.__get_dynamic_attr('author_link', obj),
            author_email = self.__get_dynamic_attr('author_email', obj),
            categories = self.__get_dynamic_attr('categories', obj),
        )

        try:
            title_template = loader.get_template('feeds/%s_title.html' % self.slug)
        except TemplateDoesNotExist:
            title_template = Template('{{ obj }}')
        try:
            description_template = loader.get_template('feeds/%s_description.html' % self.slug)
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
            author_name = self.__get_dynamic_attr('item_author_name', item)
            if author_name is not None:
                author_email = self.__get_dynamic_attr('item_author_email', item)
                author_link = self.__get_dynamic_attr('item_author_link', item)
            else:
                author_email = author_link = None
            feed.add_item(
                title = title_template.render(Context({'obj': item, 'site': current_site})).decode('utf-8'),
                link = link,
                description = description_template.render(Context({'obj': item, 'site': current_site})).decode('utf-8'),
                unique_id = link,
                enclosure = enc,
                pubdate = self.__get_dynamic_attr('item_pubdate', item),
                author_name = author_name,
                author_email = author_email,
                author_link = author_link,
                categories = self.__get_dynamic_attr('item_categories', item),
            )
        return feed
