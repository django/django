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

from thibaud.contrib.gis.gdal.datasource import DataSource
from thibaud.contrib.gis.gdal.driver import Driver
from thibaud.contrib.gis.gdal.envelope import Envelope
from thibaud.contrib.gis.gdal.error import GDALException, SRSException, check_err
from thibaud.contrib.gis.gdal.geometries import OGRGeometry
from thibaud.contrib.gis.gdal.geomtype import OGRGeomType
from thibaud.contrib.gis.gdal.libgdal import (
    GDAL_VERSION,
    gdal_full_version,
    gdal_version,
)
from thibaud.contrib.gis.gdal.raster.source import GDALRaster
from thibaud.contrib.gis.gdal.srs import AxisOrder, CoordTransform, SpatialReference

__all__ = (
    "AxisOrder",
    "Driver",
    "DataSource",
    "CoordTransform",
    "Envelope",
    "GDALException",
    "GDALRaster",
    "GDAL_VERSION",
    "OGRGeometry",
    "OGRGeomType",
    "SpatialReference",
    "SRSException",
    "check_err",
    "gdal_version",
    "gdal_full_version",
)
