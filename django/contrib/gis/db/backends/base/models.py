import re

from django.contrib.gis import gdal
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class SpatialRefSysMixin(object):
    """
    The SpatialRefSysMixin is a class used by the database-dependent
    SpatialRefSys objects to reduce redundant code.
    """
    # For pulling out the spheroid from the spatial reference string. This
    # regular expression is used only if the user does not have GDAL installed.
    # TODO: Flattening not used in all ellipsoids, could also be a minor axis,
    # or 'b' parameter.
    spheroid_regex = re.compile(r'.+SPHEROID\[\"(?P<name>.+)\",(?P<major>\d+(\.\d+)?),(?P<flattening>\d{3}\.\d+),')

    # For pulling out the units on platforms w/o GDAL installed.
    # TODO: Figure out how to pull out angular units of projected coordinate system and
    # fix for LOCAL_CS types.  GDAL should be highly recommended for performing
    # distance queries.
    units_regex = re.compile(r'.+UNIT ?\["(?P<unit_name>[\w \.\'\(\)]+)", ?(?P<unit>[^ ,\]]+)', re.DOTALL)

    @property
    def srs(self):
        """
        Returns a GDAL SpatialReference object, if GDAL is installed.
        """
        if gdal.HAS_GDAL:
            # TODO: Is caching really necessary here?  Is complexity worth it?
            if hasattr(self, '_srs'):
                # Returning a clone of the cached SpatialReference object.
                return self._srs.clone()
            else:
                # Attempting to cache a SpatialReference object.

                # Trying to get from WKT first.
                try:
                    self._srs = gdal.SpatialReference(self.wkt)
                    return self.srs
                except Exception as e:
                    msg = e

                try:
                    self._srs = gdal.SpatialReference(self.proj4text)
                    return self.srs
                except Exception as e:
                    msg = e

                raise Exception('Could not get OSR SpatialReference from WKT: %s\nError:\n%s' % (self.wkt, msg))
        else:
            raise Exception('GDAL is not installed.')

    @property
    def ellipsoid(self):
        """
        Returns a tuple of the ellipsoid parameters:
        (semimajor axis, semiminor axis, and inverse flattening).
        """
        if gdal.HAS_GDAL:
            return self.srs.ellipsoid
        else:
            m = self.spheroid_regex.match(self.wkt)
            if m:
                return (float(m.group('major')), float(m.group('flattening')))
            else:
                return None

    @property
    def name(self):
        "Returns the projection name."
        return self.srs.name

    @property
    def spheroid(self):
        "Returns the spheroid name for this spatial reference."
        return self.srs['spheroid']

    @property
    def datum(self):
        "Returns the datum for this spatial reference."
        return self.srs['datum']

    @property
    def projected(self):
        "Is this Spatial Reference projected?"
        if gdal.HAS_GDAL:
            return self.srs.projected
        else:
            return self.wkt.startswith('PROJCS')

    @property
    def local(self):
        "Is this Spatial Reference local?"
        if gdal.HAS_GDAL:
            return self.srs.local
        else:
            return self.wkt.startswith('LOCAL_CS')

    @property
    def geographic(self):
        "Is this Spatial Reference geographic?"
        if gdal.HAS_GDAL:
            return self.srs.geographic
        else:
            return self.wkt.startswith('GEOGCS')

    @property
    def linear_name(self):
        "Returns the linear units name."
        if gdal.HAS_GDAL:
            return self.srs.linear_name
        elif self.geographic:
            return None
        else:
            m = self.units_regex.match(self.wkt)
            return m.group('unit_name')

    @property
    def linear_units(self):
        "Returns the linear units."
        if gdal.HAS_GDAL:
            return self.srs.linear_units
        elif self.geographic:
            return None
        else:
            m = self.units_regex.match(self.wkt)
            return m.group('unit')

    @property
    def angular_name(self):
        "Returns the name of the angular units."
        if gdal.HAS_GDAL:
            return self.srs.angular_name
        elif self.projected:
            return None
        else:
            m = self.units_regex.match(self.wkt)
            return m.group('unit_name')

    @property
    def angular_units(self):
        "Returns the angular units."
        if gdal.HAS_GDAL:
            return self.srs.angular_units
        elif self.projected:
            return None
        else:
            m = self.units_regex.match(self.wkt)
            return m.group('unit')

    @property
    def units(self):
        "Returns a tuple of the units and the name."
        if self.projected or self.local:
            return (self.linear_units, self.linear_name)
        elif self.geographic:
            return (self.angular_units, self.angular_name)
        else:
            return (None, None)

    @classmethod
    def get_units(cls, wkt):
        """
        Return a tuple of (unit_value, unit_name) for the given WKT without
        using any of the database fields.
        """
        if gdal.HAS_GDAL:
            return gdal.SpatialReference(wkt).units
        else:
            m = cls.units_regex.match(wkt)
            return float(m.group('unit')), m.group('unit_name')

    @classmethod
    def get_spheroid(cls, wkt, string=True):
        """
        Class method used by GeometryField on initialization to
        retrieve the `SPHEROID[..]` parameters from the given WKT.
        """
        if gdal.HAS_GDAL:
            srs = gdal.SpatialReference(wkt)
            sphere_params = srs.ellipsoid
            sphere_name = srs['spheroid']
        else:
            m = cls.spheroid_regex.match(wkt)
            if m:
                sphere_params = (float(m.group('major')), float(m.group('flattening')))
                sphere_name = m.group('name')
            else:
                return None

        if not string:
            return sphere_name, sphere_params
        else:
            # `string` parameter used to place in format acceptable by PostGIS
            if len(sphere_params) == 3:
                radius, flattening = sphere_params[0], sphere_params[2]
            else:
                radius, flattening = sphere_params
            return 'SPHEROID["%s",%s,%s]' % (sphere_name, radius, flattening)

    def __str__(self):
        """
        Returns the string representation.  If GDAL is installed,
        it will be 'pretty' OGC WKT.
        """
        try:
            return six.text_type(self.srs)
        except Exception:
            return six.text_type(self.wkt)
