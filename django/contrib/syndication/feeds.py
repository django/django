from datetime import datetime, timedelta

from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.template import loader, Template, TemplateDoesNotExist
from django.contrib.sites.models import Site, RequestSite
from django.utils import feedgenerator
from django.utils.tzinfo import FixedOffset
from django.utils.encoding import smart_unicode, iri_to_uri
from django.conf import settings         
from django.template import RequestContext

def add_domain(domain, url):
    if not (url.startswith('http://') or url.startswith('https://')):
        # 'url' must already be ASCII and URL-quoted, so no need for encoding
        # conversions here.
        url = iri_to_uri(u'http://%s%s' % (domain, url))
    return url

class FeedDoesNotExist(ObjectDoesNotExist):
    pass

class Feed(object):
    item_pubdate = None
    item_enclosure_url = None
    feed_type = feedgenerator.DefaultFeed
    feed_url = None
    title_template = None
    description_template = None

    def __init__(self, slug, request):
        self.slug = slug
        self.request = request
        self.feed_url = self.feed_url or request.path
        self.title_template_name = self.title_template or ('feeds/%s_title.html' % slug)
        self.description_template_name = self.description_template or ('feeds/%s_description.html' % slug)

    def item_link(self, item):
        try:
            return item.get_absolute_url()
        except AttributeError:
            raise ImproperlyConfigured("Give your %s class a get_absolute_url() method, or define an item_link() method in your Feed class." % item.__class__.__name__)

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

    def feed_extra_kwargs(self, obj):
        """
        Returns an extra keyword arguments dictionary that is used when
        initializing the feed generator.
        """
        return {}

    def item_extra_kwargs(self, item):
        """
        Returns an extra keyword arguments dictionary that is used with
        the `add_item` call of the feed generator.
        """
        return {}

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

        if Site._meta.installed:
            current_site = Site.objects.get_current()
        else:
            current_site = RequestSite(self.request)
        
        link = self.__get_dynamic_attr('link', obj)
        link = add_domain(current_site.domain, link)

        feed = self.feed_type(
            title = self.__get_dynamic_attr('title', obj),
            subtitle = self.__get_dynamic_attr('subtitle', obj),
            link = link,
            description = self.__get_dynamic_attr('description', obj),
            language = settings.LANGUAGE_CODE.decode(),
            feed_url = add_domain(current_site.domain,
                                  self.__get_dynamic_attr('feed_url', obj)),
            author_name = self.__get_dynamic_attr('author_name', obj),
            author_link = self.__get_dynamic_attr('author_link', obj),
            author_email = self.__get_dynamic_attr('author_email', obj),
            categories = self.__get_dynamic_attr('categories', obj),
            feed_copyright = self.__get_dynamic_attr('feed_copyright', obj),
            feed_guid = self.__get_dynamic_attr('feed_guid', obj),
            ttl = self.__get_dynamic_attr('ttl', obj),
            **self.feed_extra_kwargs(obj)
        )

        try:
            title_tmp = loader.get_template(self.title_template_name)
        except TemplateDoesNotExist:
            title_tmp = Template('{{ obj }}')
        try:
            description_tmp = loader.get_template(self.description_template_name)
        except TemplateDoesNotExist:
            description_tmp = Template('{{ obj }}')

        for item in self.__get_dynamic_attr('items', obj):
            link = add_domain(current_site.domain, self.__get_dynamic_attr('item_link', item))
            enc = None
            enc_url = self.__get_dynamic_attr('item_enclosure_url', item)
            if enc_url:
                enc = feedgenerator.Enclosure(
                    url = smart_unicode(enc_url),
                    length = smart_unicode(self.__get_dynamic_attr('item_enclosure_length', item)),
                    mime_type = smart_unicode(self.__get_dynamic_attr('item_enclosure_mime_type', item))
                )
            author_name = self.__get_dynamic_attr('item_author_name', item)
            if author_name is not None:
                author_email = self.__get_dynamic_attr('item_author_email', item)
                author_link = self.__get_dynamic_attr('item_author_link', item)
            else:
                author_email = author_link = None

            pubdate = self.__get_dynamic_attr('item_pubdate', item)
            if pubdate and not pubdate.tzinfo:
                now = datetime.now()
                utcnow = datetime.utcnow()

                # Must always subtract smaller time from larger time here.
                if utcnow > now:
                    sign = -1
                    tzDifference = (utcnow - now)
                else:
                    sign = 1
                    tzDifference = (now - utcnow)

                # Round the timezone offset to the nearest half hour.
                tzOffsetMinutes = sign * ((tzDifference.seconds / 60 + 15) / 30) * 30
                tzOffset = timedelta(minutes=tzOffsetMinutes)
                pubdate = pubdate.replace(tzinfo=FixedOffset(tzOffset))

            feed.add_item(
                title = title_tmp.render(RequestContext(self.request, {'obj': item, 'site': current_site})),
                link = link,
                description = description_tmp.render(RequestContext(self.request, {'obj': item, 'site': current_site})),
                unique_id = self.__get_dynamic_attr('item_guid', item, link),
                enclosure = enc,
                pubdate = pubdate,
                author_name = author_name,
                author_email = author_email,
                author_link = author_link,
                categories = self.__get_dynamic_attr('item_categories', item),
                item_copyright = self.__get_dynamic_attr('item_copyright', item),
                **self.item_extra_kwargs(item)
            )
        return feed
