"""
 Models for the PostGIS/OGC database tables.
"""
import re
from django.db import models

# Checking for the presence of GDAL (needed for the SpatialReference object)
from django.contrib.gis.gdal import HAS_GDAL
if HAS_GDAL:
    from django.contrib.gis.gdal import SpatialReference

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
        return "%s.%s - %dD %s field (SRID: %d)" % \
               (self.f_table_name, self.f_geometry_column,
                self.coord_dimension, self.type, self.srid)

# This is the global 'spatial_ref_sys' table from PostGIS.
#   See PostGIS Documentation at Ch. 4.2.1
class SpatialRefSys(models.Model):
    srid = models.IntegerField(primary_key=True)
    auth_name = models.CharField(maxlength=256)
    auth_srid = models.IntegerField()
    srtext = models.CharField(maxlength=2048)
    proj4text = models.CharField(maxlength=2048)

    class Meta:
        db_table = 'spatial_ref_sys'

    @property
    def srs(self):
        """
        Returns a GDAL SpatialReference object, if GDAL is installed.
        """
        if HAS_GDAL:
            if hasattr(self, '_srs'):
                # Returning a clone of the cached SpatialReference object.
                return self._srs.clone()
            else:
                # Attempting to cache a SpatialReference object.

                # Trying to get from WKT first
                try:
                    self._srs = SpatialReference(self.srtext, 'wkt')
                    return self._srs.clone()
                except Exception, msg1:
                    pass

                # Trying the proj4 text next
                try:
                    self._srs = SpatialReference(self.proj4text, 'proj4')
                    return self._srs.clone()
                except Exception, msg2:
                    pass

                raise Exception, 'Could not get an OSR Spatial Reference:\n\tWKT error: %s\n\tPROJ.4 error: %s' % (msg1, msg2)
        else:
            raise Exception, 'GDAL is not installed!'
                                                                                
    @property
    def ellipsoid(self):
        """
        Returns a tuple of the ellipsoid parameters:
        (semimajor axis, semiminor axis, and inverse flattening).
        """
        if HAS_GDAL:
            return self.srs.ellipsoid
        else:
            m = spheroid_regex.match(self.srtext)
            if m: return (float(m.group('major')), float(m.group('flattening')))
            else: return None

    @property
    def name(self):
        "Returns the projection name."
        return self.srs.name

    @property
    def spheroid(self):
        "Returns the spheroid for this spatial reference."
        return self.srs['spheroid']

    @property
    def datum(self):
        "Returns the datum for this spatial reference."
        return self.srs['datum']

    @property
    def projected(self):
        "Is this Spatial Reference projected?"
        return self.srs.projected

    @property
    def local(self):
        "Is this Spatial Reference local?"
        return self.srs.local

    @property
    def geographic(self):
        "Is this Spatial Reference geographic?"
        return self.srs.geographic

    @property
    def linear_name(self):
        "Returns the linear units name."
        return self.srs.linear_name

    @property
    def linear_units(self):
        "Returns the linear units."
        return self.srs.linear_units

    @property
    def angular_units(self):
        "Returns the angular units."
        return self.srs.angular_units

    @property
    def angular_name(self):
        "Returns the name of the angular units."
        return self.srs.angular_name

    def __str__(self):
        """
        Returns the string representation.  If GDAL is installed,
        it will be 'pretty' OGC WKT.
        """
        if HAS_GDAL: return str(self.srs)
        else: return "%d:%s " % (self.srid, self.auth_name)
