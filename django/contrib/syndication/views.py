from calendar import timegm
from contextlib import suppress

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.http import Http404, HttpResponse
from django.template import TemplateDoesNotExist, loader
from django.utils import feedgenerator
from django.utils.encoding import iri_to_uri
from django.utils.html import escape
from django.utils.http import http_date
from django.utils.timezone import get_default_timezone, is_naive, make_aware


def add_domain(domain, url, secure=False):
    protocol = 'https' if secure else 'http'
    if url.startswith('//'):
        # Support network-path reference (see #16753) - RSS requires a protocol
        url = '%s:%s' % (protocol, url)
    elif not url.startswith(('http://', 'https://', 'mailto:')):
        url = iri_to_uri('%s://%s%s' % (protocol, domain, url))
    return url


class FeedDoesNotExist(ObjectDoesNotExist):
    pass


class Feed:
    feed_type = feedgenerator.DefaultFeed
    title_template = None
    description_template = None

    def __call__(self, request, *args, **kwargs):
        try:
            obj = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            raise Http404('Feed object does not exist.')
        feedgen = self.get_feed(obj, request)
        response = HttpResponse(content_type=feedgen.content_type)
        if hasattr(self, 'item_pubdate') or hasattr(self, 'item_updateddate'):
            # if item_pubdate or item_updateddate is defined for the feed, set
            # header so as ConditionalGetMiddleware is able to send 304 NOT MODIFIED
            response['Last-Modified'] = http_date(
                timegm(feedgen.latest_post_date().utctimetuple()))
        feedgen.write(response, 'utf-8')
        return response

    def item_title(self, item):
        # Titles should be double escaped by default (see #6533)
        return escape(str(item))

    def item_description(self, item):
        return str(item)

    def item_link(self, item):
        try:
            return item.get_absolute_url()
        except AttributeError:
            raise ImproperlyConfigured(
                'Give your %s class a get_absolute_url() method, or define an '
                'item_link() method in your Feed class.' % item.__class__.__name__
            )

    def item_enclosures(self, item):
        enc_url = self._get_dynamic_attr('item_enclosure_url', item)
        if enc_url:
            enc = feedgenerator.Enclosure(
                url=str(enc_url),
                length=str(self._get_dynamic_attr('item_enclosure_length', item)),
                mime_type=str(self._get_dynamic_attr('item_enclosure_mime_type', item)),
            )
            return [enc]
        return []

    def _get_dynamic_attr(self, attname, obj, default=None):
        try:
            attr = getattr(self, attname)
        except AttributeError:
            return default
        if callable(attr):
            # Check co_argcount rather than try/excepting the function and
            # catching the TypeError, because something inside the function
            # may raise the TypeError. This technique is more accurate.
            try:
                code = attr.__code__
            except AttributeError:
                code = attr.__call__.__code__
            if code.co_argcount == 2:       # one argument is 'self'
                return attr(obj)
            else:
                return attr()
        return attr

    def feed_extra_kwargs(self, obj):
        """
        Return an extra keyword arguments dictionary that is used when
        initializing the feed generator.
        """
        return {}

    def item_extra_kwargs(self, item):
        """
        Return an extra keyword arguments dictionary that is used with
        the `add_item` call of the feed generator.
        """
        return {}

    def get_object(self, request, *args, **kwargs):
        return None

    def get_context_data(self, **kwargs):
        """
        Return a dictionary to use as extra context if either
        ``self.description_template`` or ``self.item_template`` are used.

        Default implementation preserves the old behavior
        of using {'obj': item, 'site': current_site} as the context.
        """
        return {'obj': kwargs.get('item'), 'site': kwargs.get('site')}

    def get_feed(self, obj, request):
        """
        Return a feedgenerator.DefaultFeed object, fully populated, for
        this feed. Raise FeedDoesNotExist for invalid parameters.
        """
        current_site = get_current_site(request)

        link = self._get_dynamic_attr('link', obj)
        link = add_domain(current_site.domain, link, request.is_secure())

        feed = self.feed_type(
            title=self._get_dynamic_attr('title', obj),
            subtitle=self._get_dynamic_attr('subtitle', obj),
            link=link,
            description=self._get_dynamic_attr('description', obj),
            language=settings.LANGUAGE_CODE,
            feed_url=add_domain(
                current_site.domain,
                self._get_dynamic_attr('feed_url', obj) or request.path,
                request.is_secure(),
            ),
            author_name=self._get_dynamic_attr('author_name', obj),
            author_link=self._get_dynamic_attr('author_link', obj),
            author_email=self._get_dynamic_attr('author_email', obj),
            categories=self._get_dynamic_attr('categories', obj),
            feed_copyright=self._get_dynamic_attr('feed_copyright', obj),
            feed_guid=self._get_dynamic_attr('feed_guid', obj),
            ttl=self._get_dynamic_attr('ttl', obj),
            **self.feed_extra_kwargs(obj)
        )

        title_tmp = None
        if self.title_template is not None:
            with suppress(TemplateDoesNotExist):
                title_tmp = loader.get_template(self.title_template)

        description_tmp = None
        if self.description_template is not None:
            with suppress(TemplateDoesNotExist):
                description_tmp = loader.get_template(self.description_template)

        for item in self._get_dynamic_attr('items', obj):
            context = self.get_context_data(item=item, site=current_site,
                                            obj=obj, request=request)
            if title_tmp is not None:
                title = title_tmp.render(context, request)
            else:
                title = self._get_dynamic_attr('item_title', item)
            if description_tmp is not None:
                description = description_tmp.render(context, request)
            else:
                description = self._get_dynamic_attr('item_description', item)
            link = add_domain(
                current_site.domain,
                self._get_dynamic_attr('item_link', item),
                request.is_secure(),
            )
            enclosures = self._get_dynamic_attr('item_enclosures', item)
            author_name = self._get_dynamic_attr('item_author_name', item)
            if author_name is not None:
                author_email = self._get_dynamic_attr('item_author_email', item)
                author_link = self._get_dynamic_attr('item_author_link', item)
            else:
                author_email = author_link = None

            tz = get_default_timezone()

            pubdate = self._get_dynamic_attr('item_pubdate', item)
            if pubdate and is_naive(pubdate):
                pubdate = make_aware(pubdate, tz)

            updateddate = self._get_dynamic_attr('item_updateddate', item)
            if updateddate and is_naive(updateddate):
                updateddate = make_aware(updateddate, tz)

            feed.add_item(
                title=title,
                link=link,
                description=description,
                unique_id=self._get_dynamic_attr('item_guid', item, link),
                unique_id_is_permalink=self._get_dynamic_attr(
                    'item_guid_is_permalink', item),
                enclosures=enclosures,
                pubdate=pubdate,
                updateddate=updateddate,
                author_name=author_name,
                author_email=author_email,
                author_link=author_link,
                categories=self._get_dynamic_attr('item_categories', item),
                item_copyright=self._get_dynamic_attr('item_copyright', item),
                **self.item_extra_kwargs(item)
            )
        return feed
