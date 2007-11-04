"""
 This module houses ctypes interfaces for GDAL objects.  The following GDAL
  objects are supported:

 CoordTransform: Used for coordinate transformations from one spatial
  reference system to another.

 Driver: Wraps an OGR data source driver.
  
 DataSource: Wrapper for the OGR data source object, supports
  OGR-supported data sources.

 Envelope: A ctypes structure for bounding boxes (GDAL library
  not required).

 OGRGeometry: Layer for accessing OGR Geometry objects.

 OGRGeomType: A class for representing the different OGR Geometry
  types (GDAL library not required).

 SpatialReference: Represents OSR Spatial Reference objects.
"""
# Attempting to import objects that depend on the GDAL library.  The
#  HAS_GDAL flag will be set to True if the library is present on
#  the system.
try:
    from django.contrib.gis.gdal.driver import Driver
    from django.contrib.gis.gdal.datasource import DataSource
    from django.contrib.gis.gdal.libgdal import gdal_version, gdal_full_version, gdal_release_date
    from django.contrib.gis.gdal.srs import SpatialReference, CoordTransform
    from django.contrib.gis.gdal.geometries import OGRGeometry
    HAS_GDAL = True
except:
    HAS_GDAL = False

# The envelope, error, and geomtype modules do not actually require the
#  GDAL library.
from django.contrib.gis.gdal.envelope import Envelope
from django.contrib.gis.gdal.error import check_err, OGRException, OGRIndexError, SRSException
from django.contrib.gis.gdal.geomtype import OGRGeomType
