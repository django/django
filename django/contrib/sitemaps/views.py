from django.http import HttpResponse, Http404
from django.template import loader
from django.contrib.sites.models import get_current_site
from django.core import urlresolvers
from django.utils.encoding import smart_str
from django.core.paginator import EmptyPage, PageNotAnInteger

def index(request, sitemaps, template_name='sitemap_index.xml'):
    current_site = get_current_site(request)
    sites = []
    protocol = request.is_secure() and 'https' or 'http'
    for section, site in sitemaps.items():
        site.request = request
        if callable(site):
            pages = site().paginator.num_pages
        else:
            pages = site.paginator.num_pages
        sitemap_url = urlresolvers.reverse('django.contrib.sitemaps.views.sitemap', kwargs={'section': section})
        sites.append('%s://%s%s' % (protocol, current_site.domain, sitemap_url))
        if pages > 1:
            for page in range(2, pages+1):
                sites.append('%s://%s%s?p=%s' % (protocol, current_site.domain, sitemap_url, page))
    xml = loader.render_to_string(template_name, {'sitemaps': sites})
    return HttpResponse(xml, mimetype='application/xml')

def sitemap(request, sitemaps, section=None, template_name='sitemap.xml'):
    maps, urls = [], []
    if section is not None:
        if section not in sitemaps:
            raise Http404("No sitemap available for section: %r" % section)
        maps.append(sitemaps[section])
    else:
        maps = sitemaps.values()
    page = request.GET.get("p", 1)
    current_site = get_current_site(request)
    for site in maps:
        try:
            if callable(site):
                urls.extend(site().get_urls(page=page, site=current_site))
            else:
                urls.extend(site.get_urls(page=page, site=current_site))
        except EmptyPage:
            raise Http404("Page %s empty" % page)
        except PageNotAnInteger:
            raise Http404("No page '%s'" % page)
    xml = smart_str(loader.render_to_string(template_name, {'urlset': urls}))
    return HttpResponse(xml, mimetype='application/xml')
