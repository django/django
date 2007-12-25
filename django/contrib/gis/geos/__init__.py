"""
 The goal of this module is to be a ctypes wrapper around the GEOS library
 that will work on both *NIX and Windows systems.  Specifically, this uses
 the GEOS C api.

 I have several motivations for doing this:
  (1) The GEOS SWIG wrapper is no longer maintained, and requires the
      installation of SWIG.
  (2) The PCL implementation is over 2K+ lines of C and would make
      PCL a requisite package for the GeoDjango application stack.
  (3) Windows and Mac compatibility becomes substantially easier, and does not
      require the additional compilation of PCL or GEOS and SWIG -- all that
      is needed is a Win32 or Mac compiled GEOS C library (dll or dylib)
      in a location that Python can read (e.g. 'C:\Python25').

 In summary, I wanted to wrap GEOS in a more maintainable and portable way using
 only Python and the excellent ctypes library (now standard in Python 2.5).

 In the spirit of loose coupling, this library does not require Django or
 GeoDjango.  Only the GEOS C library and ctypes are needed for the platform
 of your choice.

 For more information about GEOS:
  http://geos.refractions.net
  
 For more info about PCL and the discontinuation of the Python GEOS
 library see Sean Gillies' writeup (and subsequent update) at:
  http://zcologia.com/news/150/geometries-for-python/
  http://zcologia.com/news/429/geometries-for-python-update/
"""
from django.contrib.gis.geos.base import GEOSGeometry, wkt_regex, hex_regex
from django.contrib.gis.geos.geometries import Point, LineString, LinearRing, Polygon, HAS_NUMPY
from django.contrib.gis.geos.collections import GeometryCollection, MultiPoint, MultiLineString, MultiPolygon
from django.contrib.gis.geos.error import GEOSException, GEOSIndexError
from django.contrib.gis.geos.libgeos import geos_version, geos_version_info

def fromfile(file_name):
    """
    Given a string file name, returns a GEOSGeometry. The file may contain WKB,
    WKT, or HEX.
    """
    fh = open(file_name, 'rb')
    buf = fh.read()
    fh.close()
    if wkt_regex.match(buf) or hex_regex.match(buf):
        return GEOSGeometry(buf)
    else:
        return GEOSGeometry(buffer(buf))

def fromstr(wkt_or_hex, **kwargs):
    "Given a string value (wkt or hex), returns a GEOSGeometry object."
    return GEOSGeometry(wkt_or_hex, **kwargs)

def hex_to_wkt(hex):
    "Converts HEXEWKB into WKT."
    return GEOSGeometry(hex).wkt

def wkt_to_hex(wkt):
    "Converts WKT into HEXEWKB."
    return GEOSGeometry(wkt).hex

def centroid(input):
    "Returns the centroid of the geometry (given in HEXEWKB)."
    return GEOSGeometry(input).centroid.wkt

def area(input):
    "Returns the area of the geometry (given in HEXEWKB)."
    return GEOSGeometry(input).area
    
