from warnings import warn

# GEOS is a requirement
from django.contrib.gis.geos import GEOSGeometry

# GDAL is a lot more complicated to install, and isn't necessary for many
# operations.
try:
    from django.contrib.gis.gdal import OGRGeometry, SpatialReference
    HAS_GDAL = True
except ImportError, e:
    HAS_GDAL = False

# Until model subclassing is a possibility, a mixin class is used to add
# the necessary functions that may be contributed for geographic objects.
class GeoMixin:
    "The Geographic Mixin class provides routines for geographic objects."

    # A subclass of Model is specifically needed so that these geographic
    # routines are present for instantiations of the models.
    def _get_GEOM_geos(self, field):
        "Returns a GEOS Python object for the geometry."
        warn("use model.%s" % field.attname, DeprecationWarning) 
        return getattr(self, field.attname)

    def _get_GEOM_ogr(self, field, srid):
        "Returns an OGR Python object for the geometry."
        if HAS_GDAL:
            return OGRGeometry(getattr(self, field.attname).wkt,
                               SpatialReference('EPSG:%d' % srid))
        else:
            raise Exception, "GDAL is not installed!"

    def _get_GEOM_srid(self, srid):
        "Returns the spatial reference identifier (SRID) of the geometry."
        warn("use model.geometry_field.srid", DeprecationWarning)
        return srid

    def _get_GEOM_srs(self, srid):
        "Returns ane OGR Spatial Reference object of the geometry."
        if HAS_GDAL:
            return SpatialReference('EPSG:%d' % srid)
        else:
            raise Exception, "GDAL is not installed!"

    def _get_GEOM_wkt(self, field):
        "Returns the WKT of the geometry."
        warn("use model.%s.centroid.wkt" % field.attname, DeprecationWarning) 
        return getattr(self, field.attname).wkt

    def _get_GEOM_centroid(self, field):
        "Returns the centroid of the geometry, in WKT."
        warn("use model.%s.centroid.wkt" % field.attname, DeprecationWarning) 
        return getattr(self, field.attname).centroid.wkt
    
    def _get_GEOM_area(self, field):
        "Returns the area of the geometry, in projected units."
        warn("use model.%s.area" % field.attname, DeprecationWarning)
        return getattr(self, field.attname).area
