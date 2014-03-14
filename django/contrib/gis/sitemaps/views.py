from __future__ import unicode_literals

import warnings

from django.apps import apps
from django.http import HttpResponse, Http404
from django.template import loader
from django.contrib.sites.shortcuts import get_current_site
from django.core import urlresolvers
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.contrib.gis.db.models.fields import GeometryField
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.models.fields import FieldDoesNotExist
from django.utils import six
from django.utils.deprecation import RemovedInDjango18Warning
from django.utils.translation import ugettext as _

from django.contrib.gis.shortcuts import render_to_kml, render_to_kmz


def index(request, sitemaps):
    """
    This view generates a sitemap index that uses the proper view
    for resolving geographic section sitemap URLs.
    """
    warnings.warn("Geo Sitemaps are deprecated. Use plain sitemaps from "
        "django.contrib.sitemaps instead", RemovedInDjango18Warning, stacklevel=2)
    current_site = get_current_site(request)
    sites = []
    protocol = request.scheme
    for section, site in sitemaps.items():
        if callable(site):
            pages = site().paginator.num_pages
        else:
            pages = site.paginator.num_pages
        sitemap_url = urlresolvers.reverse('django.contrib.gis.sitemaps.views.sitemap', kwargs={'section': section})
        sites.append('%s://%s%s' % (protocol, current_site.domain, sitemap_url))

        if pages > 1:
            for page in range(2, pages + 1):
                sites.append('%s://%s%s?p=%s' % (protocol, current_site.domain, sitemap_url, page))
    xml = loader.render_to_string('sitemap_index.xml', {'sitemaps': sites})
    return HttpResponse(xml, content_type='application/xml')


def sitemap(request, sitemaps, section=None):
    """
    This view generates a sitemap with additional geographic
    elements defined by Google.
    """
    warnings.warn("Geo Sitemaps are deprecated. Use plain sitemaps from "
        "django.contrib.sitemaps instead", RemovedInDjango18Warning, stacklevel=2)
    maps, urls = [], []
    if section is not None:
        if section not in sitemaps:
            raise Http404(_("No sitemap available for section: %r") % section)
        maps.append(sitemaps[section])
    else:
        maps = list(six.itervalues(sitemaps))

    page = request.GET.get("p", 1)
    current_site = get_current_site(request)
    for site in maps:
        try:
            if callable(site):
                urls.extend(site().get_urls(page=page, site=current_site))
            else:
                urls.extend(site.get_urls(page=page, site=current_site))
        except EmptyPage:
            raise Http404(_("Page %s empty") % page)
        except PageNotAnInteger:
            raise Http404(_("No page '%s'") % page)
    xml = loader.render_to_string('gis/sitemaps/geo_sitemap.xml', {'urlset': urls})
    return HttpResponse(xml, content_type='application/xml')


def kml(request, label, model, field_name=None, compress=False, using=DEFAULT_DB_ALIAS):
    """
    This view generates KML for the given app label, model, and field name.

    The model's default manager must be GeoManager, and the field name
    must be that of a geographic field.
    """
    placemarks = []
    try:
        klass = apps.get_model(label, model)
    except LookupError:
        raise Http404('You must supply a valid app label and module name.  Got "%s.%s"' % (label, model))

    if field_name:
        try:
            field, _, _, _ = klass._meta.get_field_by_name(field_name)
            if not isinstance(field, GeometryField):
                raise FieldDoesNotExist
        except FieldDoesNotExist:
            raise Http404('Invalid geometry field.')

    connection = connections[using]

    if connection.ops.postgis:
        # PostGIS will take care of transformation.
        placemarks = klass._default_manager.using(using).kml(field_name=field_name)
    else:
        # There's no KML method on Oracle or MySQL, so we use the `kml`
        # attribute of the lazy geometry instead.
        placemarks = []
        if connection.ops.oracle:
            qs = klass._default_manager.using(using).transform(4326, field_name=field_name)
        else:
            qs = klass._default_manager.using(using).all()
        for mod in qs:
            mod.kml = getattr(mod, field_name).kml
            placemarks.append(mod)

    # Getting the render function and rendering to the correct.
    if compress:
        render = render_to_kmz
    else:
        render = render_to_kml
    return render('gis/kml/placemarks.kml', {'places': placemarks})


def kmz(request, label, model, field_name=None, using=DEFAULT_DB_ALIAS):
    """
    This view returns KMZ for the given app label, model, and field name.
    """
    return kml(request, label, model, field_name, compress=True, using=using)
