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
from types import UnicodeType, TupleType
from ctypes import byref, c_char_p, c_int, c_void_p

# Getting the error checking routine and exceptions
from django.contrib.gis.gdal.error import OGRException, SRSException
from django.contrib.gis.gdal.prototypes.srs import *

#### Spatial Reference class. ####
class SpatialReference(object):
    """
    A wrapper for the OGRSpatialReference object.  According to the GDAL website,
    the SpatialReference object "provide[s] services to represent coordinate 
    systems (projections and datums) and to transform between them."
    """

    # Well-Known Geographical Coordinate System Name
    _well_known = {'WGS84':4326, 'WGS72':4322, 'NAD27':4267, 'NAD83':4269}
    _epsg_regex = re.compile('^(EPSG:)?(?P<epsg>\d+)$', re.I)
    _proj_regex = re.compile(r'^\+proj')

    #### Python 'magic' routines ####
    def __init__(self, srs_input='', srs_type='wkt'):
        """
        Creates a GDAL OSR Spatial Reference object from the given input.
        The input may be string of OGC Well Known Text (WKT), an integer 
        EPSG code, a PROJ.4 string, and/or a projection "well known" shorthand 
        string (one of 'WGS84', 'WGS72', 'NAD27', 'NAD83').
        """
        # Intializing pointer and string buffer.
        self._ptr = None
        buf = c_char_p('')

        if isinstance(srs_input, basestring):
            # Encoding to ASCII if unicode passed in.
            if isinstance(srs_input, UnicodeType):
                srs_input = srs_input.encode('ascii')

            epsg_m = self._epsg_regex.match(srs_input)
            proj_m = self._proj_regex.match(srs_input)
            if epsg_m:
                # Is this an EPSG well known name?    
                srs_type = 'epsg'
                srs_input = int(epsg_m.group('epsg'))
            elif proj_m:
                # Is the string a PROJ.4 string?
                srs_type = 'proj'
            elif srs_input in self._well_known:
                # Is this a short-hand well known name?  
                srs_type = 'epsg'
                srs_input = self._well_known[srs_input]
            elif srs_type == 'proj':
                pass
            else:
                # Setting the buffer with WKT, PROJ.4 string, etc.
                buf = c_char_p(srs_input)
        elif isinstance(srs_input, int):
            # EPSG integer code was input.
            if srs_type != 'epsg': srs_type = 'epsg'
        elif isinstance(srs_input, c_void_p):
            srs_type = 'ogr'
        else:
            raise TypeError('Invalid SRS type "%s"' % srs_type)

        if srs_type == 'ogr':
            # SRS input is OGR pointer
            srs = srs_input
        else:
            # Creating a new pointer, using the string buffer.
            srs = new_srs(buf)

        # If the pointer is NULL, throw an exception.
        if not srs:
            raise SRSException('Could not create spatial reference from: %s' % srs_input)
        else:
            self._ptr = srs

        # Post-processing if in PROJ.4 or EPSG formats.
        if srs_type == 'proj': self.import_proj(srs_input)
        elif srs_type == 'epsg': self.import_epsg(srs_input)

    def __del__(self):
        "Destroys this spatial reference."
        if self._ptr: release_srs(self._ptr)

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

    def __str__(self):
        "The string representation uses 'pretty' WKT."
        return self.pretty_wkt

    #### SpatialReference Methods ####
    def attr_value(self, target, index=0):
        """
        The attribute value for the given target node (e.g. 'PROJCS'). The index
        keyword specifies an index of the child node to return.
        """
        if not isinstance(target, str) or not isinstance(index, int):
            raise TypeError
        return get_attr_value(self._ptr, target, index)

    def auth_name(self, target):
        "Returns the authority name for the given string target node."
        return get_auth_name(self._ptr, target)
    
    def auth_code(self, target):
        "Returns the authority code for the given string target node."
        return get_auth_code(self._ptr, target)

    def clone(self):
        "Returns a clone of this SpatialReference object."
        return SpatialReference(clone_srs(self._ptr))

    def from_esri(self):
        "Morphs this SpatialReference from ESRI's format to EPSG."
        morph_from_esri(self._ptr)

    def identify_epsg(self):
        """
        This method inspects the WKT of this SpatialReference, and will
        add EPSG authority nodes where an EPSG identifier is applicable.
        """
        identify_epsg(self._ptr)

    def to_esri(self):
        "Morphs this SpatialReference to ESRI's format."
        morph_to_esri(self._ptr)

    def validate(self):
        "Checks to see if the given spatial reference is valid."
        srs_validate(self._ptr)
    
    #### Name & SRID properties ####
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
    @property
    def linear_name(self):
        "Returns the name of the linear units."
        units, name = linear_units(self._ptr, byref(c_char_p()))
        return name

    @property
    def linear_units(self):
        "Returns the value of the linear units."
        units, name = linear_units(self._ptr, byref(c_char_p()))
        return units

    @property
    def angular_name(self):
        "Returns the name of the angular units."
        units, name = angular_units(self._ptr, byref(c_char_p()))
        return name

    @property
    def angular_units(self):
        "Returns the value of the angular units."
        units, name = angular_units(self._ptr, byref(c_char_p()))
        return units

    @property
    def units(self):
        """
        Returns a 2-tuple of the units value and the units name, 
        and will automatically determines whether to return the linear
        or angular units.
        """
        if self.projected or self.local:
            return linear_units(self._ptr, byref(c_char_p()))
        elif self.geographic:
            return angular_units(self._ptr, byref(c_char_p()))
        else:
            return (None, None)

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
        return semi_major(self._ptr, byref(c_int()))

    @property
    def semi_minor(self):
        "Returns the Semi Minor Axis for this Spatial Reference."
        return semi_minor(self._ptr, byref(c_int()))

    @property
    def inverse_flattening(self):
        "Returns the Inverse Flattening for this Spatial Reference."
        return invflattening(self._ptr, byref(c_int()))

    #### Boolean Properties ####
    @property
    def geographic(self):
        """
        Returns True if this SpatialReference is geographic 
         (root node is GEOGCS).
        """
        return bool(isgeographic(self._ptr))

    @property
    def local(self):
        "Returns True if this SpatialReference is local (root node is LOCAL_CS)."
        return bool(islocal(self._ptr))

    @property
    def projected(self):
        """
        Returns True if this SpatialReference is a projected coordinate system 
         (root node is PROJCS).
        """
        return bool(isprojected(self._ptr))

    #### Import Routines #####
    def import_wkt(self, wkt):
        "Imports the Spatial Reference from OGC WKT (string)"
        from_wkt(self._ptr, byref(c_char_p(wkt)))

    def import_proj(self, proj):
        "Imports the Spatial Reference from a PROJ.4 string."
        from_proj(self._ptr, proj)

    def import_epsg(self, epsg):
        "Imports the Spatial Reference from the EPSG code (an integer)."
        from_epsg(self._ptr, epsg)

    def import_xml(self, xml):
        "Imports the Spatial Reference from an XML string."
        from_xml(self._ptr, xml)

    #### Export Properties ####
    @property
    def wkt(self):
        "Returns the WKT representation of this Spatial Reference."
        return to_wkt(self._ptr, byref(c_char_p()))

    @property
    def pretty_wkt(self, simplify=0):
        "Returns the 'pretty' representation of the WKT."
        return to_pretty_wkt(self._ptr, byref(c_char_p()), simplify)

    @property
    def proj(self):
        "Returns the PROJ.4 representation for this Spatial Reference."
        return to_proj(self._ptr, byref(c_char_p()))

    @property
    def proj4(self):
        "Alias for proj()."
        return self.proj

    @property
    def xml(self, dialect=''):
        "Returns the XML representation of this Spatial Reference."
        # FIXME: This leaks memory, have to figure out why.
        return to_xml(self._ptr, byref(c_char_p()), dialect)

    def to_esri(self):
        "Morphs this SpatialReference to ESRI's format."
        morph_to_esri(self._ptr)

    def from_esri(self):
        "Morphs this SpatialReference from ESRI's format to EPSG."
        morph_from_esri(self._ptr)

class CoordTransform(object):
    "The coordinate system transformation object."

    def __init__(self, source, target):
        "Initializes on a source and target SpatialReference objects."
        self._ptr = None # Initially NULL 
        if not isinstance(source, SpatialReference) or not isinstance(target, SpatialReference):
            raise SRSException('source and target must be of type SpatialReference')
        self._ptr = new_ct(source._ptr, target._ptr)
        if not self._ptr:
            raise SRSException('could not intialize CoordTransform object')
        self._srs1_name = source.name
        self._srs2_name = target.name

    def __del__(self):
        "Deletes this Coordinate Transformation object."
        if self._ptr: destroy_ct(self._ptr)

    def __str__(self):
        return 'Transform from "%s" to "%s"' % (self._srs1_name, self._srs2_name)
