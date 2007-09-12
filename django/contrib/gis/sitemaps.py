from django.core import urlresolvers
from django.contrib.sitemaps import Sitemap
from django.contrib.gis.db.models.fields import GeometryField
from django.contrib.gis.shortcuts import render_to_kml
from django.db.models import get_model, get_models
from django.http import HttpResponse

class KMLSitemap(Sitemap):
    """
    A minimal hook to produce KML sitemaps.
    """
    def __init__(self, locations=None):
        if locations is None:
            self.locations = _build_kml_sources()
        else:
            self.locations = locations

    def items(self):
        return self.locations

    def location(self, obj):
        return urlresolvers.reverse('django.contrib.gis.sitemaps.kml',
                                    kwargs={'label':obj[0],
                                            'field_name':obj[1]})

def _build_kml_sources():
    "Make a mapping of all available KML sources."
    ret = []
    for klass in get_models():
        for field in klass._meta.fields:
            if isinstance(field, GeometryField):
                label = "%s.%s" % (klass._meta.app_label,
                                   klass._meta.module_name)
                
                ret.append((label, field.name))
    return ret


class KMLNotFound(Exception):
    pass

def kml(request, label, field_name):
    placemarks = []
    klass = get_model(*label.split('.'))
    if not klass:
        raise KMLNotFound("You must supply a valid app.model label.  Got %s" % label)

    #FIXME: GMaps apparently has a limit on size of displayed kml files
    #  check if paginating w/ external refs (i.e. linked list) helps.
    placemarks.extend(list(klass._default_manager.kml(field_name)[:100]))

    #FIXME: other KML features?
    return render_to_kml('gis/kml/placemarks.kml', {'places' : placemarks})

    
