from django.http import HttpResponse, Http404
from django.template import loader
from django.contrib.sites.models import Site
from django.core import urlresolvers

def index(request, sitemaps):
    current_site = Site.objects.get_current()
    sites = []
    protocol = request.is_secure() and 'https' or 'http'
    for section in sitemaps.keys():
        sitemap_url = urlresolvers.reverse('django.contrib.sitemaps.views.sitemap', kwargs={'section': section})
        sites.append('%s://%s%s' % (protocol, current_site.domain, sitemap_url))
    xml = loader.render_to_string('sitemap_index.xml', {'sitemaps': sites})
    return HttpResponse(xml, mimetype='application/xml')

def sitemap(request, sitemaps, section=None):
    maps, urls = [], []
    if section is not None:
        if not sitemaps.has_key(section):
            raise Http404("No sitemap available for section: %r" % section)
        maps.append(sitemaps[section])
    else:
        maps = sitemaps.values()
    for site in maps:
        if callable(site):
            urls.extend(site().get_urls())
        else:
            urls.extend(site.get_urls())
    xml = loader.render_to_string('sitemap.xml', {'urlset': urls})
    return HttpResponse(xml, mimetype='application/xml')
