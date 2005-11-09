from django.core import rss
from django.core.exceptions import Http404
from django.utils.httpwrappers import HttpResponse

def feed(request, slug, param=None):
    try:
        f = rss.get_registered_feed(slug).get_feed(param)
    except (rss.FeedIsNotRegistered, rss.FeedDoesNotExist):
        raise Http404
    response = HttpResponse(mimetype='application/xml')
    f.write(response, 'utf-8')
    return response
