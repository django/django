import datetime
from django.conf import settings
from django.contrib.sites.models import Site, RequestSite
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.http import HttpResponse, Http404
from django.template import loader, Template, TemplateDoesNotExist, RequestContext
from django.utils import feedgenerator, tzinfo
from django.utils.encoding import force_unicode, iri_to_uri, smart_unicode
from django.utils.html import escape

def add_domain(domain, url):
    if not (url.startswith('http://')
            or url.startswith('https://')
            or url.startswith('mailto:')):
        # 'url' must already be ASCII and URL-quoted, so no need for encoding
        # conversions here.
        url = iri_to_uri(u'http://%s%s' % (domain, url))
    return url

class FeedDoesNotExist(ObjectDoesNotExist):
    pass


class Feed(object):
    feed_type = feedgenerator.DefaultFeed
    title_template = None
    description_template = None

    def __call__(self, request, *args, **kwargs):
        try:
            obj = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            raise Http404('Feed object does not exist.')
        feedgen = self.get_feed(obj, request)
        response = HttpResponse(mimetype=feedgen.mime_type)
        feedgen.write(response, 'utf-8')
        return response

    def item_title(self, item):
        # Titles should be double escaped by default (see #6533)
        return escape(force_unicode(item))

    def item_description(self, item):
        return force_unicode(item)

    def item_link(self, item):
        try:
            return item.get_absolute_url()
        except AttributeError:
            raise ImproperlyConfigured('Give your %s class a get_absolute_url() method, or define an item_link() method in your Feed class.' % item.__class__.__name__)

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

    def get_object(self, request, *args, **kwargs):
        return None

    def get_feed(self, obj, request):
        """
        Returns a feedgenerator.DefaultFeed object, fully populated, for
        this feed. Raises FeedDoesNotExist for invalid parameters.
        """
        if Site._meta.installed:
            current_site = Site.objects.get_current()
        else:
            current_site = RequestSite(request)

        link = self.__get_dynamic_attr('link', obj)
        link = add_domain(current_site.domain, link)

        feed = self.feed_type(
            title = self.__get_dynamic_attr('title', obj),
            subtitle = self.__get_dynamic_attr('subtitle', obj),
            link = link,
            description = self.__get_dynamic_attr('description', obj),
            language = settings.LANGUAGE_CODE.decode(),
            feed_url = add_domain(current_site.domain,
                    self.__get_dynamic_attr('feed_url', obj) or request.path),
            author_name = self.__get_dynamic_attr('author_name', obj),
            author_link = self.__get_dynamic_attr('author_link', obj),
            author_email = self.__get_dynamic_attr('author_email', obj),
            categories = self.__get_dynamic_attr('categories', obj),
            feed_copyright = self.__get_dynamic_attr('feed_copyright', obj),
            feed_guid = self.__get_dynamic_attr('feed_guid', obj),
            ttl = self.__get_dynamic_attr('ttl', obj),
            **self.feed_extra_kwargs(obj)
        )

        title_tmp = None
        if self.title_template is not None:
            try:
                title_tmp = loader.get_template(self.title_template)
            except TemplateDoesNotExist:
                pass

        description_tmp = None
        if self.description_template is not None:
            try:
                description_tmp = loader.get_template(self.description_template)
            except TemplateDoesNotExist:
                pass

        for item in self.__get_dynamic_attr('items', obj):
            if title_tmp is not None:
                title = title_tmp.render(RequestContext(request, {'obj': item, 'site': current_site}))
            else:
                title = self.__get_dynamic_attr('item_title', item)
            if description_tmp is not None:
                description = description_tmp.render(RequestContext(request, {'obj': item, 'site': current_site}))
            else:
                description = self.__get_dynamic_attr('item_description', item)
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
                now = datetime.datetime.now()
                utcnow = datetime.datetime.utcnow()

                # Must always subtract smaller time from larger time here.
                if utcnow > now:
                    sign = -1
                    tzDifference = (utcnow - now)
                else:
                    sign = 1
                    tzDifference = (now - utcnow)

                # Round the timezone offset to the nearest half hour.
                tzOffsetMinutes = sign * ((tzDifference.seconds / 60 + 15) / 30) * 30
                tzOffset = datetime.timedelta(minutes=tzOffsetMinutes)
                pubdate = pubdate.replace(tzinfo=tzinfo.FixedOffset(tzOffset))

            feed.add_item(
                title = title,
                link = link,
                description = description,
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


def feed(request, url, feed_dict=None):
    """Provided for backwards compatibility."""
    import warnings
    warnings.warn('The syndication feed() view is deprecated. Please use the '
                  'new class based view API.',
                  category=PendingDeprecationWarning)

    if not feed_dict:
        raise Http404("No feeds are registered.")

    try:
        slug, param = url.split('/', 1)
    except ValueError:
        slug, param = url, ''

    try:
        f = feed_dict[slug]
    except KeyError:
        raise Http404("Slug %r isn't registered." % slug)

    try:
        feedgen = f(slug, request).get_feed(param)
    except FeedDoesNotExist:
        raise Http404("Invalid feed parameters. Slug %r is valid, but other parameters, or lack thereof, are not." % slug)

    response = HttpResponse(mimetype=feedgen.mime_type)
    feedgen.write(response, 'utf-8')
    return response

