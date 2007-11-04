"""
  The Spatial Reference class, represensents OGR Spatial Reference objects.

  Example:
  >>> from django.contrib.gis.gdal import SpatialReference
  >>> srs = SpatialReference('WGS84')
  >>> print srs
  GEOGCS["WGS 84",
      DATUM["WGS_1984",
          SPHEROID["WGS 84",6378137,298.257223563,
              AUTHORITY["EPSG","7030"]],
          TOWGS84[0,0,0,0,0,0,0],
          AUTHORITY["EPSG","6326"]],
      PRIMEM["Greenwich",0,
          AUTHORITY["EPSG","8901"]],
      UNIT["degree",0.01745329251994328,
          AUTHORITY["EPSG","9122"]],
      AUTHORITY["EPSG","4326"]]
  >>> print srs.proj
  +proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs
  >>> print srs.ellipsoid
  (6378137.0, 6356752.3142451793, 298.25722356300003)
  >>> print srs.projected, srs.geographic
  False True
  >>> srs.import_epsg(32140)
  >>> print srs.name
  NAD83 / Texas South Central
"""
import re
from types import StringType, UnicodeType, TupleType
from ctypes import \
     c_char_p, c_int, c_double, c_void_p, POINTER, \
     byref, string_at, create_string_buffer

# Getting the GDAL C Library
from django.contrib.gis.gdal.libgdal import lgdal

# Getting the error checking routine and exceptions
from django.contrib.gis.gdal.error import check_err, OGRException, SRSException

#### ctypes function prototypes ####
def ellipsis_func(f):
    """
    Creates a ctypes function prototype for OSR ellipsis property functions, e.g., 
     OSRGetSemiMajor, OSRGetSemiMinor, OSRGetInvFlattening.
    """
    f.restype = c_double
    f.argtypes = [c_void_p, POINTER(c_int)]
    return f

# Getting the semi_major, semi_minor, and flattening functions.
semi_major = ellipsis_func(lgdal.OSRGetSemiMajor)
semi_minor = ellipsis_func(lgdal.OSRGetSemiMinor)
invflattening = ellipsis_func(lgdal.OSRGetInvFlattening)

def units_func(f):
    """
    Creates a ctypes function prototype for OSR units functions, e.g., 
     OSRGetAngularUnits, OSRGetLinearUnits.
    """
    f.restype = c_double
    f.argtypes = [c_void_p, POINTER(c_char_p)]
    return f

# Getting the angular_units, linear_units functions
linear_units = units_func(lgdal.OSRGetLinearUnits)
angular_units = units_func(lgdal.OSRGetAngularUnits)

#### Spatial Reference class. ####
class SpatialReference(object):
    """
    A wrapper for the OGRSpatialReference object.  According to the GDAL website,
    the SpatialReference object 'provide[s] services to represent coordinate 
    systems (projections and datums) and to transform between them.'
    """

    # Well-Known Geographical Coordinate System Name
    _well_known = {'WGS84':4326, 'WGS72':4322, 'NAD27':4267, 'NAD83':4269}
    _epsg_regex = re.compile('^EPSG:(?P<epsg>\d+)$', re.I)

    #### Python 'magic' routines ####
    def __init__(self, srs_input='', srs_type='wkt'):
        "Creates a spatial reference object from the given OGC Well Known Text (WKT)."

        self._srs = None # Initially NULL

        # Creating an initial empty string buffer.
        buf = c_char_p('')

        # Encoding to ASCII if unicode passed in.
        if isinstance(srs_input, UnicodeType):
            srs_input = srs_input.encode('ascii')

        if isinstance(srs_input, StringType):
            # Is this an EPSG well known name?
            m = self._epsg_regex.match(srs_input)
            if m:
                srs_type = 'epsg'
                srs_input = int(m.group('epsg'))
            # Is this a short-hand well known name?
            elif srs_input in self._well_known:
                srs_type = 'epsg'
                srs_input = self._well_known[srs_input]
            elif srs_type == 'proj':
                pass
            else:
                buf = c_char_p(srs_input)
        elif isinstance(srs_input, int):
            if srs_type == 'wkt': srs_type = 'epsg' # want to try epsg if only integer provided
            if srs_type not in ('epsg', 'ogr'): 
                raise SRSException('Integer input requires SRS type of "ogr" or "epsg".')
        else:
            raise TypeError('Invalid SRS type "%s"' % srs_type)

        # Calling OSRNewSpatialReference with the string buffer.
        if srs_type == 'ogr':
            srs = srs_input # SRS input is OGR pointer
        else:
            srs = lgdal.OSRNewSpatialReference(buf)

        # If the pointer is NULL, throw an exception.
        if not srs:
            raise SRSException('Could not create spatial reference from: %s' % srs_input)
        else:
            self._srs = srs

        # Post-processing if in PROJ.4 or EPSG formats.
        if srs_type == 'proj': self.import_proj(srs_input)
        elif srs_type == 'epsg': self.import_epsg(srs_input)

    def __del__(self):
        "Destroys this spatial reference."
        if self._srs: lgdal.OSRRelease(self._srs)

    def __getitem__(self, target):
        """
        Returns the value of the given string attribute node, None if the node 
        doesn't exist.  Can also take a tuple as a parameter, (target, child), 
        where child is the index of the attribute in the WKT.  For example:

        >>> wkt = 'GEOGCS["WGS 84", DATUM["WGS_1984, ... AUTHORITY["EPSG","4326"]]')
        >>> srs = SpatialReference(wkt) # could also use 'WGS84', or 4326
        >>> print srs['GEOGCS']
        WGS 84
        >>> print srs['DATUM']
        WGS_1984
        >>> print srs['AUTHORITY']
        EPSG
        >>> print srs['AUTHORITY', 1] # The authority value
        4326
        >>> print srs['TOWGS84', 4] # the fourth value in this wkt
        0
        >>> print srs['UNIT|AUTHORITY'] # For the units authority, have to use the pipe symbole.
        EPSG
        >>> print srs['UNIT|AUTHORITY', 1] # The authority value for the untis
        9122
        """
        if isinstance(target, TupleType):
            return self.attr_value(*target)
        else:
            return self.attr_value(target)

    def __nonzero__(self):
        "Returns True if this SpatialReference object is valid."
        try:
            self.validate()
            return True
        except OGRException:
            return False

    def __str__(self):
        "The string representation uses 'pretty' WKT."
        return self.pretty_wkt

    def _string_ptr(self, ptr):
        """
        Returns the string at the pointer if it is valid, None if the pointer
        is NULL.
        """
        if not ptr: return None
        else: return string_at(ptr)

    #### SpatialReference Methods ####
    def auth_name(self, target):
        "Getting the authority name for the target node."
        ptr = lgdal.OSRGetAuthorityName(self._srs, c_char_p(target))
        return self._string_ptr(ptr)
    
    def auth_code(self, target):
        "Getting the authority code for the given target node."
        ptr = lgdal.OSRGetAuthorityCode(self._srs, c_char_p(target))
        return self._string_ptr(ptr)

    def attr_value(self, target, index=0):
        """
        The attribute value for the given target node (e.g. 'PROJCS'). The index
        keyword specifies an index of the child node to return.
        """
        if not isinstance(target, str):
            raise TypeError('Attribute target must be a string')
        ptr = lgdal.OSRGetAttrValue(self._srs, c_char_p(target), c_int(index))
        return self._string_ptr(ptr)

    def validate(self):
        "Checks to see if the given spatial reference is valid."
        check_err(lgdal.OSRValidate(self._srs))
    
    def clone(self):
        "Returns a clone of this Spatial Reference."
        return SpatialReference(lgdal.OSRClone(self._srs), 'ogr')

    @property
    def name(self):
        "Returns the name of this Spatial Reference."
        if self.projected: return self.attr_value('PROJCS')
        elif self.geographic: return self.attr_value('GEOGCS')
        elif self.local: return self.attr_value('LOCAL_CS')
        else: return None

    @property
    def srid(self):
        "Returns the SRID of top-level authority, or None if undefined."
        try:
            return int(self.attr_value('AUTHORITY', 1))
        except (TypeError, ValueError):
            return None
        
    #### Unit Properties ####
    def _cache_linear(self):
        "Caches the linear units value and name."
        if not hasattr(self, '_linear_units') or not hasattr(self, '_linear_name'):
            name_buf = c_char_p()
            self._linear_units = linear_units(self._srs, byref(name_buf))
            self._linear_name = string_at(name_buf)

    @property
    def linear_name(self):
        "Returns the name of the linear units."
        self._cache_linear()
        return self._linear_name

    @property
    def linear_units(self):
        "Returns the value of the linear units."
        self._cache_linear()
        return self._linear_units

    def _cache_angular(self):
        "Caches the angular units value and name."
        name_buf = c_char_p()
        if not hasattr(self, '_angular_units') or not hasattr(self, '_angular_name'):
            self._angular_units = angular_units(self._srs, byref(name_buf))
            self._angular_name = string_at(name_buf)

    @property
    def angular_name(self):
        "Returns the name of the angular units."
        self._cache_angular()
        return self._angular_name

    @property
    def angular_units(self):
        "Returns the value of the angular units."
        self._cache_angular()
        return self._angular_units

    #### Spheroid/Ellipsoid Properties ####
    @property
    def ellipsoid(self):
        """
        Returns a tuple of the ellipsoid parameters:
         (semimajor axis, semiminor axis, and inverse flattening)
        """
        return (self.semi_major, self.semi_minor, self.inverse_flattening)

    @property
    def semi_major(self):
        "Returns the Semi Major Axis for this Spatial Reference."
        err = c_int(0)
        sm = semi_major(self._srs, byref(err))
        check_err(err.value)
        return sm

    @property
    def semi_minor(self):
        "Returns the Semi Minor Axis for this Spatial Reference."
        err = c_int()
        sm = semi_minor(self._srs, byref(err))
        check_err(err.value)
        return sm

    @property
    def inverse_flattening(self):
        "Returns the Inverse Flattening for this Spatial Reference."
        err = c_int()
        inv_flat = invflattening(self._srs, byref(err))
        check_err(err.value)
        return inv_flat

    #### Boolean Properties ####
    @property
    def geographic(self):
        """
        Returns True if this SpatialReference is geographic 
         (root node is GEOGCS).
        """
        if lgdal.OSRIsGeographic(self._srs): return True
        else: return False

    @property
    def local(self):
        "Returns True if this SpatialReference is local (root node is LOCAL_CS)."
        if lgdal.OSRIsLocal(self._srs): return True
        else: return False

    @property
    def projected(self):
        """
        Returns True if this SpatialReference is a projected coordinate system 
         (root node is PROJCS).
        """
        if lgdal.OSRIsProjected(self._srs): return True
        else: return False

    #### Import Routines #####
    def import_wkt(self, wkt):
        "Imports the Spatial Reference from OGC WKT (string)"
        buf = create_string_buffer(wkt)
        check_err(lgdal.OSRImportFromWkt(self._srs, byref(buf)))

    def import_proj(self, proj):
        "Imports the Spatial Reference from a PROJ.4 string."
        check_err(lgdal.OSRImportFromProj4(self._srs, create_string_buffer(proj)))

    def import_epsg(self, epsg):
        "Imports the Spatial Reference from the EPSG code (an integer)."
        check_err(lgdal.OSRImportFromEPSG(self._srs, c_int(epsg)))

    def import_xml(self, xml):
        "Imports the Spatial Reference from an XML string."
        check_err(lgdal.OSRImportFromXML(self._srs, create_string_buffer(xml)))

    #### Export Properties ####
    @property
    def wkt(self):
        "Returns the WKT representation of this Spatial Reference."
        w = c_char_p()
        check_err(lgdal.OSRExportToWkt(self._srs, byref(w)))
        if w: return string_at(w)

    @property
    def pretty_wkt(self, simplify=0):
        "Returns the 'pretty' representation of the WKT."
        w = c_char_p()
        check_err(lgdal.OSRExportToPrettyWkt(self._srs, byref(w), c_int(simplify)))
        if w: return string_at(w)

    @property
    def proj(self):
        "Returns the PROJ.4 representation for this Spatial Reference."
        w = c_char_p()
        check_err(lgdal.OSRExportToProj4(self._srs, byref(w)))
        if w: return string_at(w)

    @property
    def proj4(self):
        "Alias for proj()."
        return self.proj

    @property
    def xml(self, dialect=''):
        "Returns the XML representation of this Spatial Reference."
        w = c_char_p()
        check_err(lgdal.OSRExportToXML(self._srs, byref(w), create_string_buffer(dialect)))
        return string_at(w)

class CoordTransform(object):
    "A coordinate system transformation object."

    def __init__(self, source, target):
        "Initializes on a source and target SpatialReference objects."
        self._ct = 0 # Initially NULL 
        if not isinstance(source, SpatialReference) or not isinstance(target, SpatialReference):
            raise SRSException('source and target must be of type SpatialReference')
        ct = lgdal.OCTNewCoordinateTransformation(source._srs, target._srs)
        if not ct:
            raise SRSException('could not intialize CoordTransform object')
        self._ct = ct
        self._srs1_name = source.name
        self._srs2_name = target.name

    def __del__(self):
        "Deletes this Coordinate Transformation object."
        if self._ct: lgdal.OCTDestroyCoordinateTransformation(self._ct)

    def __str__(self):
        return 'Transform from "%s" to "%s"' % (str(self._srs1_name), str(self._srs2_name))
