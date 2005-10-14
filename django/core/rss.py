from django.core.exceptions import ObjectDoesNotExist
from django.core.template import Context, loader
from django.models.core import sites
from django.utils import feedgenerator
from django.conf.settings import LANGUAGE_CODE, SETTINGS_MODULE

class FeedConfiguration:
    def __init__(self, slug, title_cb, link_cb, description_cb, get_list_func_cb, get_list_kwargs,
        param_func=None, param_kwargs_cb=None, get_list_kwargs_cb=None, get_pubdate_cb=None,
        enc_url=None, enc_length=None, enc_mime_type=None):
        """
        slug -- Normal Python string. Used to register the feed.

        title_cb, link_cb, description_cb -- Functions that take the param
        (if applicable) and return a normal Python string.

        get_list_func_cb -- Function that takes the param and returns a
        function to use in retrieving items.

        get_list_kwargs -- Dictionary of kwargs to pass to the function
        returned by get_list_func_cb.

        param_func -- Function to use in retrieving the param (if applicable).

        param_kwargs_cb -- Function that takes the slug and returns a
        dictionary of kwargs to use in param_func.

        get_list_kwargs_cb -- Function that takes the param and returns a
        dictionary to use in addition to get_list_kwargs (if applicable).

        get_pubdate_cb -- Function that takes the object and returns a datetime
        to use as the publication date in the feed.

        The three enc_* parameters are strings representing methods or
        attributes to call on a particular item to get its enclosure
        information. Each of those methods/attributes should return a normal
        Python string.
        """
        self.slug = slug
        self.title_cb, self.link_cb = title_cb, link_cb
        self.description_cb = description_cb
        self.get_list_func_cb = get_list_func_cb
        self.get_list_kwargs = get_list_kwargs
        self.param_func, self.param_kwargs_cb = param_func, param_kwargs_cb
        self.get_list_kwargs_cb = get_list_kwargs_cb
        self.get_pubdate_cb = get_pubdate_cb
        assert (None == enc_url == enc_length == enc_mime_type) or (enc_url is not None and enc_length is not None and enc_mime_type is not None)
        self.enc_url = enc_url
        self.enc_length = enc_length
        self.enc_mime_type = enc_mime_type

    def get_feed(self, param_slug=None):
        """
        Returns a utils.feedgenerator.DefaultRssFeed object, fully populated,
        representing this FeedConfiguration.
        """
        if param_slug:
            try:
                param = self.param_func(**self.param_kwargs_cb(param_slug))
            except ObjectDoesNotExist:
                raise FeedIsNotRegistered
        else:
            param = None
        current_site = sites.get_current()
        f = self._get_feed_generator_object(param)
        title_template = loader.get_template('rss/%s_title' % self.slug)
        description_template = loader.get_template('rss/%s_description' % self.slug)
        kwargs = self.get_list_kwargs.copy()
        if param and self.get_list_kwargs_cb:
            kwargs.update(self.get_list_kwargs_cb(param))
        get_list_func = self.get_list_func_cb(param)
        for obj in get_list_func(**kwargs):
            link = obj.get_absolute_url()
            if not link.startswith('http://'):
                link = u'http://%s%s' % (current_site.domain, link)
            enc = None
            if self.enc_url:
                enc_url = getattr(obj, self.enc_url)
                enc_length = getattr(obj, self.enc_length)
                enc_mime_type = getattr(obj, self.enc_mime_type)
                try:
                    enc_url = enc_url()
                except TypeError:
                    pass
                try:
                    enc_length = enc_length()
                except TypeError:
                    pass
                try:
                    enc_mime_type = enc_mime_type()
                except TypeError:
                    pass
                enc = feedgenerator.Enclosure(enc_url.decode('utf-8'),
                    (enc_length and str(enc_length).decode('utf-8') or ''), enc_mime_type.decode('utf-8'))
            f.add_item(
                title = title_template.render(Context({'obj': obj, 'site': current_site})).decode('utf-8'),
                link = link,
                description = description_template.render(Context({'obj': obj, 'site': current_site})).decode('utf-8'),
                unique_id=link,
                enclosure=enc,
                pubdate = self.get_pubdate_cb and self.get_pubdate_cb(obj) or None,
            )
        return f

    def _get_feed_generator_object(self, param):
        current_site = sites.get_current()
        link = self.link_cb(param).decode()
        if not link.startswith('http://'):
            link = u'http://%s%s' % (current_site.domain, link)
        return feedgenerator.DefaultRssFeed(
            title = self.title_cb(param).decode(),
            link = link,
            description = self.description_cb(param).decode(),
            language = LANGUAGE_CODE.decode(),
        )


# global dict used by register_feed and get_registered_feed
_registered_feeds = {}

class FeedIsNotRegistered(Exception):
    pass

class FeedRequiresParam(Exception):
    pass

def register_feed(feed):
    _registered_feeds[feed.slug] = feed

def get_registered_feed(slug):
    # try to load a RSS settings module so that feeds can be registered
    try:
        __import__(SETTINGS_MODULE + '_rss', '', '', [''])
    except (KeyError, ImportError, ValueError):
        pass
    try:
        return _registered_feeds[slug]
    except KeyError:
        raise FeedIsNotRegistered

