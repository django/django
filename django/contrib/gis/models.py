"""
 Imports the SpatialRefSys and GeometryColumns models dependent on the
 spatial database backend.
"""
import re
from django.conf import settings

# Checking for the presence of GDAL (needed for the SpatialReference object)
from django.contrib.gis.gdal import HAS_GDAL
if HAS_GDAL:
    from django.contrib.gis.gdal import SpatialReference

# For pulling out the spheroid from the spatial reference string. This
# regular expression is used only if the user does not have GDAL installed.
#  TODO: Flattening not used in all ellipsoids, could also be a minor axis, or 'b'
#        parameter.
spheroid_regex = re.compile(r'.+SPHEROID\[\"(?P<name>.+)\",(?P<major>\d+(\.\d+)?),(?P<flattening>\d{3}\.\d+),')

class SpatialRefSysMixin(object):
    """
    The SpatialRefSysMixin is a class used by the database-dependent
    SpatialRefSys objects to reduce redundnant code.
    """
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

                # Trying to get from WKT first.
                try:
                    self._srs = SpatialReference(self.wkt)
                    return self.srs
                except Exception, msg:
                    pass
                
                raise Exception('Could not get OSR SpatialReference from WKT: %s\nError:\n%s' % (self.wkt, msg))
        else:
            raise Exception('GDAL is not installed.')

    @property
    def ellipsoid(self):
        """
        Returns a tuple of the ellipsoid parameters:
        (semimajor axis, semiminor axis, and inverse flattening).
        """
        if HAS_GDAL:
            return self.srs.ellipsoid
        else:
            m = spheroid_regex.match(self.wkt)
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

    def __unicode__(self):
        """
        Returns the string representation.  If GDAL is installed,
        it will be 'pretty' OGC WKT.
        """
        try:
            return unicode(self.srs)
        except:
            return unicode(self.srtext)

# The SpatialRefSys and GeometryColumns models
if settings.DATABASE_ENGINE == 'postgresql_psycopg2':
    from django.contrib.gis.db.backend.postgis.models import GeometryColumns, SpatialRefSys
elif settings.DATABASE_ENGINE == 'oracle':
    from django.contrib.gis.db.backend.oracle.models import GeometryColumns, SpatialRefSys
else:
    raise NotImplementedError('No SpatialRefSys or GeometryColumns models for backend: %s' % settings.DATABASE_ENGINE)
