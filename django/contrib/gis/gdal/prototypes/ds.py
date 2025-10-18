"""
This module houses the ctypes function prototypes for OGR DataSource
related data structures. OGR_Dr_*, OGR_DS_*, OGR_L_*, OGR_F_*,
OGR_Fld_* routines are relevant here.
"""

from ctypes import POINTER, c_char_p, c_double, c_int, c_long, c_uint, c_void_p

from django.contrib.gis.gdal.envelope import OGREnvelope
from django.contrib.gis.gdal.prototypes.generation import (
    BoolOutput,
    ConstStringOutput,
    DoubleOutput,
    GeomOutput,
    Int64Output,
    IntOutput,
    SRSOutput,
    VoidOutput,
    VoidPtrOutput,
)

c_int_p = POINTER(c_int)  # shortcut type

GDAL_OF_READONLY = 0x00
GDAL_OF_UPDATE = 0x01

GDAL_OF_ALL = 0x00
GDAL_OF_RASTER = 0x02
GDAL_OF_VECTOR = 0x04

# Driver Routines
register_all = VoidOutput("GDALAllRegister", argtypes=[], errcheck=False)
cleanup_all = VoidOutput("GDALDestroyDriverManager", argtypes=[], errcheck=False)
get_driver = VoidPtrOutput("GDALGetDriver", argtypes=[c_int])
get_driver_by_name = VoidPtrOutput(
    "GDALGetDriverByName", argtypes=[c_char_p], errcheck=False
)
get_driver_count = IntOutput("GDALGetDriverCount", argtypes=[])
get_driver_description = ConstStringOutput("GDALGetDescription", argtypes=[c_void_p])

# DataSource
open_ds = VoidPtrOutput(
    "GDALOpenEx",
    argtypes=[
        c_char_p,
        c_uint,
        POINTER(c_char_p),
        POINTER(c_char_p),
        POINTER(c_char_p),
    ],
)
destroy_ds = VoidOutput("GDALClose", argtypes=[c_void_p], errcheck=False)
get_ds_name = ConstStringOutput("GDALGetDescription", argtypes=[c_void_p])
get_dataset_driver = VoidPtrOutput("GDALGetDatasetDriver", argtypes=[c_void_p])
get_layer = VoidPtrOutput("GDALDatasetGetLayer", argtypes=[c_void_p, c_int])
get_layer_by_name = VoidPtrOutput(
    "GDALDatasetGetLayerByName", argtypes=[c_void_p, c_char_p]
)
get_layer_count = IntOutput("GDALDatasetGetLayerCount", argtypes=[c_void_p])


# Layer Routines
get_extent = VoidOutput(
    "OGR_L_GetExtent", argtypes=[c_void_p, POINTER(OGREnvelope), c_int]
)
get_feature = VoidPtrOutput("OGR_L_GetFeature", argtypes=[c_void_p, c_long])
get_feature_count = IntOutput("OGR_L_GetFeatureCount", argtypes=[c_void_p, c_int])
get_layer_defn = VoidPtrOutput("OGR_L_GetLayerDefn", argtypes=[c_void_p])
get_layer_srs = SRSOutput("OGR_L_GetSpatialRef", argtypes=[c_void_p])
get_next_feature = VoidPtrOutput("OGR_L_GetNextFeature", argtypes=[c_void_p])
reset_reading = VoidOutput("OGR_L_ResetReading", argtypes=[c_void_p], errcheck=False)
test_capability = IntOutput("OGR_L_TestCapability", argtypes=[c_void_p, c_char_p])
get_spatial_filter = GeomOutput("OGR_L_GetSpatialFilter", argtypes=[c_void_p])
set_spatial_filter = VoidOutput(
    "OGR_L_SetSpatialFilter", argtypes=[c_void_p, c_void_p], errcheck=False
)
set_spatial_filter_rect = VoidOutput(
    "OGR_L_SetSpatialFilterRect",
    argtypes=[c_void_p, c_double, c_double, c_double, c_double],
    errcheck=False,
)

# Feature Definition Routines
get_fd_geom_type = IntOutput("OGR_FD_GetGeomType", argtypes=[c_void_p])
get_fd_name = ConstStringOutput("OGR_FD_GetName", argtypes=[c_void_p])
get_feat_name = ConstStringOutput("OGR_FD_GetName", argtypes=[c_void_p])
get_field_count = IntOutput("OGR_FD_GetFieldCount", argtypes=[c_void_p])
get_field_defn = VoidPtrOutput("OGR_FD_GetFieldDefn", argtypes=[c_void_p, c_int])

# Feature Routines
clone_feature = VoidPtrOutput("OGR_F_Clone", argtypes=[c_void_p])
destroy_feature = VoidOutput("OGR_F_Destroy", argtypes=[c_void_p], errcheck=False)
feature_equal = IntOutput("OGR_F_Equal", argtypes=[c_void_p, c_void_p])
get_feat_geom_ref = GeomOutput("OGR_F_GetGeometryRef", argtypes=[c_void_p])
get_feat_field_count = IntOutput("OGR_F_GetFieldCount", argtypes=[c_void_p])
get_feat_field_defn = VoidPtrOutput("OGR_F_GetFieldDefnRef", argtypes=[c_void_p, c_int])
get_fid = IntOutput("OGR_F_GetFID", argtypes=[c_void_p])
get_field_as_datetime = IntOutput(
    "OGR_F_GetFieldAsDateTime",
    argtypes=[c_void_p, c_int, c_int_p, c_int_p, c_int_p, c_int_p, c_int_p, c_int_p],
)
get_field_as_double = DoubleOutput("OGR_F_GetFieldAsDouble", argtypes=[c_void_p, c_int])
get_field_as_integer = IntOutput("OGR_F_GetFieldAsInteger", argtypes=[c_void_p, c_int])
get_field_as_integer64 = Int64Output(
    "OGR_F_GetFieldAsInteger64", argtypes=[c_void_p, c_int]
)
is_field_set = BoolOutput("OGR_F_IsFieldSetAndNotNull", argtypes=[c_void_p, c_int])
get_field_as_string = ConstStringOutput(
    "OGR_F_GetFieldAsString", argtypes=[c_void_p, c_int]
)
get_field_index = IntOutput("OGR_F_GetFieldIndex", argtypes=[c_void_p, c_char_p])

# Field Routines
get_field_name = ConstStringOutput("OGR_Fld_GetNameRef", argtypes=[c_void_p])
get_field_precision = IntOutput("OGR_Fld_GetPrecision", argtypes=[c_void_p])
get_field_type = IntOutput("OGR_Fld_GetType", argtypes=[c_void_p])
get_field_type_name = ConstStringOutput("OGR_GetFieldTypeName", argtypes=[c_int])
get_field_width = IntOutput("OGR_Fld_GetWidth", argtypes=[c_void_p])
