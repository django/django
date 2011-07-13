from django.http import Http404

def feed(request, url, feed_dict=None):
    """Provided for backwards compatibility."""
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

    instance = f()
    instance.feed_url = getattr(f, 'feed_url', None) or request.path
    instance.title_template = f.title_template or ('feeds/%s_title.html' % slug)
    instance.description_template = f.description_template or ('feeds/%s_description.html' % slug)
    return instance(request)
