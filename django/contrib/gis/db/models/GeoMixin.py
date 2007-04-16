# GEOS Routines
from django.contrib.gis.geos import GEOSGeometry, hex_to_wkt, centroid, area

# Until model subclassing is a possibility, a mixin class is used to add
# the necessary functions that may be contributed for geographic objects.
class GeoMixin:
    "The Geographic Mixin class, provides routines for geographic objects."

    # A subclass of Model is specifically needed so that these geographic
    # routines are present for instantiations of the models.
    def _get_GEOM_geos(self, field):
        "Gets a GEOS Python object for the geometry."
        return GEOSGeometry(getattr(self, field.attname), 'hex')

    def _get_GEOM_wkt(self, field):
        "Gets the WKT of the geometry."
        hex = getattr(self, field.attname)
        return hex_to_wkt(hex)

    def _get_GEOM_centroid(self, field):
        "Gets the centroid of the geometry, in WKT."
        hex = getattr(self, field.attname)
        return centroid(hex)
    
    def _get_GEOM_area(self, field):
        "Gets the area of the geometry, in projected units."
        hex = getattr(self, field.attname)
        return area(hex)


