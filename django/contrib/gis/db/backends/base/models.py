from operator import attrgetter

from django.contrib.gis import gdal


class SpatialRefSysMixin:
    """
    The SpatialRefSysMixin is a class used by the database-dependent
    SpatialRefSys objects to reduce redundant code.
    """
    @property
    def srs(self):
        """
        Return a GDAL SpatialReference object.
        """
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

    ellipsoid = property(
        attrgetter('srs.ellipsoid'), None, None,
        """
        Return a tuple of the ellipsoid parameters:
        (semimajor axis, semiminor axis, and inverse flattening).
        """
    )
    name = property(
        attrgetter('srs.name'), None, None,
        "Return the projection name."
    )

    @property
    def spheroid(self):
        "Return the spheroid name for this spatial reference."
        return self.srs['spheroid']

    @property
    def datum(self):
        "Return the datum for this spatial reference."
        return self.srs['datum']

    projected = property(
        attrgetter('srs.projected'), None, None,
        "Is this Spatial Reference projected?"
    )
    local = property(
        attrgetter('srs.local'), None, None,
        "Is this Spatial Reference local?"
    )
    geographic = property(
        attrgetter('srs.geographic'), None, None,
        "Is this Spatial Reference geographic?"
    )
    linear_name = property(
        attrgetter('srs.linear_name'), None, None,
        "Return the linear units name."
    )
    linear_units = property(
        attrgetter('srs.linear_units'), None, None,
        "Return the linear units."
    )
    angular_name = property(
        attrgetter('srs.angular_name'), None, None,
        "Return the name of the angular units."
    )
    angular_units = property(
        attrgetter('srs.angular_units'), None, None,
        "Return the angular units."
    )

    @property
    def units(self):
        "Return a tuple of the units and the name."
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
        return gdal.SpatialReference(wkt).units

    @classmethod
    def get_spheroid(cls, wkt, string=True):
        """
        Class method used by GeometryField on initialization to
        retrieve the `SPHEROID[..]` parameters from the given WKT.
        """
        srs = gdal.SpatialReference(wkt)
        sphere_params = srs.ellipsoid
        sphere_name = srs['spheroid']

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
        Return the string representation, a 'pretty' OGC WKT.
        """
        return str(self.srs)
