from django.http import HttpResponse, Http404
from django.template import loader
from django.contrib.gis.db.backend import SpatialBackend
from django.contrib.sites.models import Site
from django.core import urlresolvers
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.db.models import get_model
from django.utils.encoding import smart_str

from django.contrib.gis.shortcuts import render_to_kml, render_to_kmz

class KMLNotFound(Exception):
    pass

def index(request, sitemaps):
    """
    This view generates a sitemap index that uses the proper view
    for resolving geographic section sitemap URLs.
    """
    current_site = Site.objects.get_current()
    sites = []
    protocol = request.is_secure() and 'https' or 'http'
    for section, site in sitemaps.items():
        if callable(site):
            pages = site().paginator.num_pages
        else:
            pages = site.paginator.num_pages
        sitemap_url = urlresolvers.reverse('django.contrib.gis.sitemaps.views.sitemap', kwargs={'section': section})
        sites.append('%s://%s%s' % (protocol, current_site.domain, sitemap_url))
      
        if pages > 1:
            for page in range(2, pages+1):
                sites.append('%s://%s%s?p=%s' % (protocol, current_site.domain, sitemap_url, page))
    xml = loader.render_to_string('sitemap_index.xml', {'sitemaps': sites})
    return HttpResponse(xml, mimetype='application/xml')

def sitemap(request, sitemaps, section=None):
    """
    This view generates a sitemap with additional geographic
    elements defined by Google.
    """
    maps, urls = [], []
    if section is not None:
        if section not in sitemaps:
            raise Http404("No sitemap available for section: %r" % section)
        maps.append(sitemaps[section])
    else:
        maps = sitemaps.values()

    page = request.GET.get("p", 1)
    for site in maps:
        try:
            if callable(site):
                urls.extend(site().get_urls(page))
            else:
                urls.extend(site.get_urls(page))
        except EmptyPage:
            raise Http404("Page %s empty" % page)
        except PageNotAnInteger:
            raise Http404("No page '%s'" % page)
    xml = smart_str(loader.render_to_string('gis/sitemaps/geo_sitemap.xml', {'urlset': urls}))
    return HttpResponse(xml, mimetype='application/xml')

def kml(request, label, model, field_name=None, compress=False):
    """
    This view generates KML for the given app label, model, and field name.

    The model's default manager must be GeoManager, and the field name
    must be that of a geographic field.
    """
    placemarks = []
    klass = get_model(label, model)
    if not klass:
        raise KMLNotFound("You must supply a valid app.model label.  Got %s.%s" % (label, model))

    if SpatialBackend.postgis:
        # PostGIS will take care of transformation.
        placemarks = klass._default_manager.kml(field_name=field_name)
    else:
        # There's no KML method on Oracle or MySQL, so we use the `kml`
        # attribute of the lazy geometry instead.
        placemarks = []
        if SpatialBackend.oracle:
            qs = klass._default_manager.transform(4326, field_name=field_name)
        else:
            qs = klass._default_manager.all()
        for mod in qs:
            setattr(mod, 'kml', getattr(mod, field_name).kml)
            placemarks.append(mod)

    # Getting the render function and rendering to the correct.
    if compress:
        render = render_to_kmz
    else:
        render = render_to_kml
    return render('gis/kml/placemarks.kml', {'places' : placemarks})

def kmz(request, label, model, field_name=None):
    """
    This view returns KMZ for the given app label, model, and field name.
    """
    return kml(request, label, model, field_name, True)
