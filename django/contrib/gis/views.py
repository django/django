from django.http import Http404
from django.utils.translation import ugettext as _


def feed(request, url, feed_dict=None):
    """Provided for backwards compatibility."""
    if not feed_dict:
        raise Http404(_("No feeds are registered."))

    slug = url.partition('/')[0]
    try:
        f = feed_dict[slug]
    except KeyError:
        raise Http404(_("Slug %r isn't registered.") % slug)

    instance = f()
    instance.feed_url = getattr(f, 'feed_url', None) or request.path
    instance.title_template = f.title_template or ('feeds/%s_title.html' % slug)
    instance.description_template = f.description_template or ('feeds/%s_description.html' % slug)
    return instance(request)
