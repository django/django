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

class SpatialRefSysMixin(object):
    """
    The SpatialRefSysMixin is a class used by the database-dependent
    SpatialRefSys objects to reduce redundnant code.
    """

    # For pulling out the spheroid from the spatial reference string. This
    # regular expression is used only if the user does not have GDAL installed.
    #  TODO: Flattening not used in all ellipsoids, could also be a minor axis, or 'b'
    #        parameter.
    spheroid_regex = re.compile(r'.+SPHEROID\[\"(?P<name>.+)\",(?P<major>\d+(\.\d+)?),(?P<flattening>\d{3}\.\d+),')

    # For pulling out the units on platforms w/o GDAL installed.
    # TODO: Figure out how to pull out angular units of projected coordinate system and
    # fix for LOCAL_CS types.  GDAL should be highly recommended for performing 
    # distance queries.
    units_regex = re.compile(r'.+UNIT ?\["(?P<unit_name>[\w \'\(\)]+)", ?(?P<unit>[\d\.]+)(,AUTHORITY\["(?P<unit_auth_name>[\w \'\(\)]+)","(?P<unit_auth_val>\d+)"\])?\]([\w ]+)?(,AUTHORITY\["(?P<auth_name>[\w \'\(\)]+)","(?P<auth_val>\d+)"\])?\]$')
    
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
            m = self.spheroid_regex.match(self.wkt)
            if m: return (float(m.group('major')), float(m.group('flattening')))
            else: return None

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
        if HAS_GDAL:
            return self.srs.projected
        else:
            return self.wkt.startswith('PROJCS')

    @property
    def local(self):
        "Is this Spatial Reference local?"
        if HAS_GDAL:
            return self.srs.local
        else:
            return self.wkt.startswith('LOCAL_CS')

    @property
    def geographic(self):
        "Is this Spatial Reference geographic?"
        if HAS_GDAL:
            return self.srs.geographic
        else:
            return self.wkt.startswith('GEOGCS')

    @property
    def linear_name(self):
        "Returns the linear units name."
        if HAS_GDAL:
            return self.srs.linear_name
        elif self.geographic: 
            return None
        else:
            m = self.units_regex.match(self.wkt)
            return m.group('unit_name')
                
    @property
    def linear_units(self):
        "Returns the linear units."
        if HAS_GDAL:
            return self.srs.linear_units
        elif self.geographic:
            return None
        else:
            m = self.units_regex.match(self.wkt)
            return m.group('unit')

    @property
    def angular_name(self):
        "Returns the name of the angular units."
        if HAS_GDAL:
            return self.srs.angular_name
        elif self.projected:
            return None
        else:
            m = self.units_regex.match(self.wkt)
            return m.group('unit_name')

    @property
    def angular_units(self):
        "Returns the angular units."
        if HAS_GDAL:
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
        Class method used by GeometryField on initialization to
        retrive the units on the given WKT, without having to use
        any of the database fields.
        """
        if HAS_GDAL:
            return SpatialReference(wkt).units
        else:
            m = cls.units_regex.match(wkt)
            return m.group('unit'), m.group('unit_name')

    @classmethod
    def get_spheroid(cls, wkt, string=True):
        """
        Class method used by GeometryField on initialization to
        retrieve the `SPHEROID[..]` parameters from the given WKT.
        """
        if HAS_GDAL:
            srs = SpatialReference(wkt)
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

    def __unicode__(self):
        """
        Returns the string representation.  If GDAL is installed,
        it will be 'pretty' OGC WKT.
        """
        try:
            return unicode(self.srs)
        except:
            return unicode(self.wkt)

# The SpatialRefSys and GeometryColumns models
_srid_info = True
if settings.DATABASE_ENGINE == 'postgresql_psycopg2':
    # Because the PostGIS version is checked when initializing the spatial 
    # backend a `ProgrammingError` will be raised if the PostGIS tables 
    # and functions are not installed.  We catch here so it won't be raised when 
    # running the Django test suite.
    from psycopg2 import ProgrammingError
    try:
        from django.contrib.gis.db.backend.postgis.models import GeometryColumns, SpatialRefSys
    except ProgrammingError:
        _srid_info = False
elif settings.DATABASE_ENGINE == 'oracle':
    # Same thing as above, except the GEOS library is attempted to be loaded for
    # `BaseSpatialBackend`, and an exception will be raised during the
    # Django test suite if it doesn't exist.
    try:
        from django.contrib.gis.db.backend.oracle.models import GeometryColumns, SpatialRefSys
    except:
        _srid_info = False
else:
    _srid_info = False

if _srid_info:
    def get_srid_info(srid):
        """
        Returns the units, unit name, and spheroid WKT associated with the
        given SRID from the `spatial_ref_sys` (or equivalent) spatial database
        table.  We use a database cursor to execute the query because this
        function is used when it is not possible to use the ORM (for example,
        during field initialization).
        """
        # SRID=-1 is a common convention for indicating the geometry has no
        # spatial reference information associated with it.  Thus, we will
        # return all None values without raising an exception.
        if srid == -1: return None, None, None

        # Getting the spatial reference WKT associated with the SRID from the
        # `spatial_ref_sys` (or equivalent) spatial database table. This query
        # cannot be executed using the ORM because this information is needed
        # when the ORM cannot be used (e.g., during the initialization of 
        # `GeometryField`).
        from django.db import connection
        cur = connection.cursor()
        qn = connection.ops.quote_name
        stmt = 'SELECT %(table)s.%(wkt_col)s FROM %(table)s WHERE (%(table)s.%(srid_col)s = %(srid)s)'
        stmt = stmt % {'table' : qn(SpatialRefSys._meta.db_table),
                       'wkt_col' : qn(SpatialRefSys.wkt_col()),
                       'srid_col' : qn('srid'),
                       'srid' : srid,
                       }
        cur.execute(stmt)
        
        # Fetching the WKT from the cursor; if the query failed raise an Exception.
        fetched = cur.fetchone()
        if not fetched:
            raise ValueError('Failed to find spatial reference entry in "%s" corresponding to SRID=%s.' % 
                             (SpatialRefSys._meta.db_table, srid))
        srs_wkt = fetched[0]

        # Getting metadata associated with the spatial reference system identifier.
        # Specifically, getting the unit information and spheroid information 
        # (both required for distance queries).
        unit, unit_name = SpatialRefSys.get_units(srs_wkt)
        spheroid = SpatialRefSys.get_spheroid(srs_wkt)
        return unit, unit_name, spheroid
else:
    def get_srid_info(srid):
        """
        Dummy routine for the backends that do not have the OGC required
        spatial metadata tables (like MySQL).
        """
        return None, None, None
   
