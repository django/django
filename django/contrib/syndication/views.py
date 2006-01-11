from django.contrib.syndication import feeds
from django.core.exceptions import Http404
from django.http import HttpResponse

def feed(request, url, feed_dict=None):
    if not feed_dict:
        raise Http404, "No feeds are registered."

    try:
        slug, param = url.split('/', 1)
    except ValueError:
        slug, param = url, ''

    try:
        f = feed_dict[slug]
    except KeyError:
        raise Http404, "Slug %r isn't registered." % slug

    try:
        feedgen = f(slug, request.path).get_feed(param)
    except feeds.FeedDoesNotExist:
        raise Http404, "Invalid feed parameters. Slug %r is valid, but other parameters, or lack thereof, are not." % slug

    response = HttpResponse(mimetype=feedgen.mime_type)
    feedgen.write(response, 'utf-8')
    return response
