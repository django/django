"""
 This module houses the ctypes function prototypes for OGR DataSource
 related data structures. OGR_Dr_*, OGR_DS_*, OGR_L_*, OGR_F_*,
 OGR_Fld_* routines are relevant here.
"""
from ctypes import POINTER, c_char_p, c_double, c_int, c_long, c_void_p

from django.contrib.gis.gdal.envelope import OGREnvelope
from django.contrib.gis.gdal.libgdal import lgdal
from django.contrib.gis.gdal.prototypes.generation import (
    const_string_output, double_output, geom_output, int_output, srs_output,
    void_output, voidptr_output,
)

c_int_p = POINTER(c_int)  # shortcut type

# Driver Routines
register_all = void_output(lgdal.OGRRegisterAll, [], errcheck=False)
cleanup_all = void_output(lgdal.OGRCleanupAll, [], errcheck=False)
get_driver = voidptr_output(lgdal.OGRGetDriver, [c_int])
get_driver_by_name = voidptr_output(lgdal.OGRGetDriverByName, [c_char_p], errcheck=False)
get_driver_count = int_output(lgdal.OGRGetDriverCount, [])
get_driver_name = const_string_output(lgdal.OGR_Dr_GetName, [c_void_p], decoding='ascii')

# DataSource
open_ds = voidptr_output(lgdal.OGROpen, [c_char_p, c_int, POINTER(c_void_p)])
destroy_ds = void_output(lgdal.OGR_DS_Destroy, [c_void_p], errcheck=False)
release_ds = void_output(lgdal.OGRReleaseDataSource, [c_void_p])
get_ds_name = const_string_output(lgdal.OGR_DS_GetName, [c_void_p])
get_layer = voidptr_output(lgdal.OGR_DS_GetLayer, [c_void_p, c_int])
get_layer_by_name = voidptr_output(lgdal.OGR_DS_GetLayerByName, [c_void_p, c_char_p])
get_layer_count = int_output(lgdal.OGR_DS_GetLayerCount, [c_void_p])

# Layer Routines
get_extent = void_output(lgdal.OGR_L_GetExtent, [c_void_p, POINTER(OGREnvelope), c_int])
get_feature = voidptr_output(lgdal.OGR_L_GetFeature, [c_void_p, c_long])
get_feature_count = int_output(lgdal.OGR_L_GetFeatureCount, [c_void_p, c_int])
get_layer_defn = voidptr_output(lgdal.OGR_L_GetLayerDefn, [c_void_p])
get_layer_srs = srs_output(lgdal.OGR_L_GetSpatialRef, [c_void_p])
get_next_feature = voidptr_output(lgdal.OGR_L_GetNextFeature, [c_void_p])
reset_reading = void_output(lgdal.OGR_L_ResetReading, [c_void_p], errcheck=False)
test_capability = int_output(lgdal.OGR_L_TestCapability, [c_void_p, c_char_p])
get_spatial_filter = geom_output(lgdal.OGR_L_GetSpatialFilter, [c_void_p])
set_spatial_filter = void_output(lgdal.OGR_L_SetSpatialFilter, [c_void_p, c_void_p], errcheck=False)
set_spatial_filter_rect = void_output(lgdal.OGR_L_SetSpatialFilterRect,
    [c_void_p, c_double, c_double, c_double, c_double], errcheck=False
)

# Feature Definition Routines
get_fd_geom_type = int_output(lgdal.OGR_FD_GetGeomType, [c_void_p])
get_fd_name = const_string_output(lgdal.OGR_FD_GetName, [c_void_p])
get_feat_name = const_string_output(lgdal.OGR_FD_GetName, [c_void_p])
get_field_count = int_output(lgdal.OGR_FD_GetFieldCount, [c_void_p])
get_field_defn = voidptr_output(lgdal.OGR_FD_GetFieldDefn, [c_void_p, c_int])

# Feature Routines
clone_feature = voidptr_output(lgdal.OGR_F_Clone, [c_void_p])
destroy_feature = void_output(lgdal.OGR_F_Destroy, [c_void_p], errcheck=False)
feature_equal = int_output(lgdal.OGR_F_Equal, [c_void_p, c_void_p])
get_feat_geom_ref = geom_output(lgdal.OGR_F_GetGeometryRef, [c_void_p])
get_feat_field_count = int_output(lgdal.OGR_F_GetFieldCount, [c_void_p])
get_feat_field_defn = voidptr_output(lgdal.OGR_F_GetFieldDefnRef, [c_void_p, c_int])
get_fid = int_output(lgdal.OGR_F_GetFID, [c_void_p])
get_field_as_datetime = int_output(lgdal.OGR_F_GetFieldAsDateTime,
    [c_void_p, c_int, c_int_p, c_int_p, c_int_p, c_int_p, c_int_p, c_int_p]
)
get_field_as_double = double_output(lgdal.OGR_F_GetFieldAsDouble, [c_void_p, c_int])
get_field_as_integer = int_output(lgdal.OGR_F_GetFieldAsInteger, [c_void_p, c_int])
get_field_as_string = const_string_output(lgdal.OGR_F_GetFieldAsString, [c_void_p, c_int])
get_field_index = int_output(lgdal.OGR_F_GetFieldIndex, [c_void_p, c_char_p])

# Field Routines
get_field_name = const_string_output(lgdal.OGR_Fld_GetNameRef, [c_void_p])
get_field_precision = int_output(lgdal.OGR_Fld_GetPrecision, [c_void_p])
get_field_type = int_output(lgdal.OGR_Fld_GetType, [c_void_p])
get_field_type_name = const_string_output(lgdal.OGR_GetFieldTypeName, [c_int])
get_field_width = int_output(lgdal.OGR_Fld_GetWidth, [c_void_p])
