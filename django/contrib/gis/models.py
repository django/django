import re
from django.db import models

# Checking for the presence of GDAL
try:
    from django.contrib.gis.gdal import SpatialReference
    HAS_OSR = True
except ImportError:
    HAS_OSR = False

"""
  Models for the PostGIS/OGC database tables.
"""

# For pulling out the spheroid from the spatial reference string. This
# regular expression is used only if the user does not have GDAL installed.
#  TODO: Flattening not used in all ellipsoids, could also be a minor axis, or 'b'
#        parameter.
spheroid_regex = re.compile(r'.+SPHEROID\[\"(?P<name>.+)\",(?P<major>\d+(\.\d+)?),(?P<flattening>\d{3}\.\d+),')

# This is the global 'geometry_columns' from PostGIS.
#   See PostGIS Documentation at Ch. 4.2.2
class GeometryColumns(models.Model):
    f_table_catalog = models.CharField(maxlength=256)
    f_table_schema = models.CharField(maxlength=256)
    f_table_name = models.CharField(maxlength=256, primary_key=True)
    f_geometry_column = models.CharField(maxlength=256)
    coord_dimension = models.IntegerField()
    srid = models.IntegerField()
    type = models.CharField(maxlength=30)

    class Meta:
        db_table = 'geometry_columns'

    def __str__(self):
        return "%s.%s - %dD %s field (SRID: %d)" % (self.f_table_name, self.f_geometry_column, self.coord_dimension, self.type, self.srid)

# This is the global 'spatial_ref_sys' table from PostGIS.
#   See PostGIS Documentation at Ch. 4.2.1
class SpatialRefSys(models.Model):
    srid = models.IntegerField(primary_key=True)
    auth_name = models.CharField(maxlength=256)
    auth_srid = models.IntegerField()
    srtext = models.CharField(maxlength=2048)
    proj4 = models.CharField(maxlength=2048, db_column='proj4text')

    class Meta:
        db_table = 'spatial_ref_sys'

    def _cache_osr(self):
        "Caches a GDAL OSR object for this Spatial Reference."
        if HAS_OSR:
            if not hasattr(self, '_srs'):
                # Trying to get from WKT first
                try:
                    self._srs = SpatialReference(self.srtext, 'wkt')
                    return
                except:
                    pass

                # Trying the proj4 text next
                try:
                    self._srs = SpatialReference(self.proj4, 'proj4')
                    return
                except:
                    pass

                raise Exception, 'Could not get a OSR Spatial Reference.'
        else:
            raise Exception, 'GDAL is not installed!'

    @property
    def srs(self):
        self._cache_osr()
        return self._srs.clone()
                                                                                
    @property
    def ellipsoid(self):
        """Returns a tuple of the ellipsoid parameters:
        (semimajor axis, semiminor axis, and inverse flattening)."""
        if HAS_OSR:
            # Setting values initially to False
            self._cache_osr()
            major = self._srs.semi_major
            minor = self._srs.semi_minor
            invflat  = self._srs.inverse_flattening
            return (major, minor, invflat)
        else:
            m = spheroid_regex.match(self.srtext)
            if m: return (float(m.group('major')), float(m.group('flattening')))
            else: return None

    @property
    def name(self):
        "Returns the projection name."
        self._cache_osr()
        return self._srs.name

    @property
    def spheroid(self):
        "Returns the spheroid for this spatial reference."
        self._cache_osr()
        return self._srs['spheroid']

    @property
    def datum(self):
        "Returns the datum for this spatial reference."
        self._cache_osr()
        return self._srs['datum']

    @property
    def projected(self):
        "Is this Spatial Reference projected?"
        self._cache_osr()
        return self._srs.projected

    @property
    def local(self):
        "Is this Spatial Reference local?"
        self._cache_osr()
        return self._srs.local

    @property
    def geographic(self):
        "Is this Spatial Reference geographic?"
        self._cache_osr()
        return self._srs.geographic

    @property
    def linear_name(self):
        "Returns the linear units name."
        self._cache_osr()
        return self._srs.linear_name

    @property
    def linear_units(self):
        "Returns the linear units."
        self._cache_osr()
        return self._srs.linear_units

    @property
    def angular_units(self):
        "Returns the angular units."
        self._cache_osr()
        return self._srs.angular_units

    @property
    def angular_name(self):
        "Returns the name of the angular units."
        self._cache_osr()
        return self._srs.angular_name

    def __str__(self):
        "Returns the string representation.  If GDAL is installed, it will be 'pretty' OGC WKT."
        if HAS_OSR:
            self._cache_osr()
            if hasattr(self, '_srs'): return str(self._srs)
        return "%d:%s " % (self.srid, self.auth_name)
