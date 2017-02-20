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

 OGRGeometry: Object for accessing OGR Geometry functionality.

 OGRGeomType: A class for representing the different OGR Geometry
  types (GDAL library not required).

 SpatialReference: Represents OSR Spatial Reference objects.

 The GDAL library will be imported from the system path using the default
 library name for the current OS. The default library path may be overridden
 by setting `GDAL_LIBRARY_PATH` in your settings with the path to the GDAL C
 library on your system.
"""
from django.contrib.gis.gdal.envelope import Envelope
from django.contrib.gis.gdal.error import (  # NOQA
    GDALException, OGRException, OGRIndexError, SRSException, check_err,
)
from django.contrib.gis.gdal.geomtype import OGRGeomType  # NOQA

__all__ = [
    'check_err', 'Envelope', 'GDALException', 'OGRException', 'OGRIndexError',
    'SRSException', 'OGRGeomType', 'HAS_GDAL',
]

# Attempting to import objects that depend on the GDAL library.  The
# HAS_GDAL flag will be set to True if the library is present on
# the system.
try:
    from django.contrib.gis.gdal.driver import Driver  # NOQA
    from django.contrib.gis.gdal.datasource import DataSource  # NOQA
    from django.contrib.gis.gdal.libgdal import gdal_version, gdal_full_version, GDAL_VERSION  # NOQA
    from django.contrib.gis.gdal.raster.source import GDALRaster  # NOQA
    from django.contrib.gis.gdal.srs import SpatialReference, CoordTransform  # NOQA
    from django.contrib.gis.gdal.geometries import OGRGeometry  # NOQA
    HAS_GDAL = True
    __all__ += [
        'Driver', 'DataSource', 'gdal_version', 'gdal_full_version',
        'GDALRaster', 'GDAL_VERSION', 'SpatialReference', 'CoordTransform',
        'OGRGeometry',
    ]
except GDALException:
    HAS_GDAL = False
