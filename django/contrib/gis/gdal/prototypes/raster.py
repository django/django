"""
This module houses the ctypes function prototypes for GDAL DataSource (raster)
related data structures.
"""

from ctypes import POINTER, c_bool, c_char_p, c_double, c_int, c_void_p
from functools import partial

from django.contrib.gis.gdal.prototypes.generation import (
    CharArrayOutput,
    ConstStringOutput,
    DoubleOutput,
    IntOutput,
    VoidOutput,
    VoidPtrOutput,
)

# For more detail about c function names and definitions see
# https://gdal.org/api/raster_c_api.html
# https://gdal.org/doxygen/gdalwarper_8h.html
# https://gdal.org/api/gdal_utils.html

# Prepare partial functions that use cpl error codes
VoidOutput = partial(VoidOutput, cpl=True)
ConstStringOutput = partial(ConstStringOutput, cpl=True)
DoubleOutput = partial(DoubleOutput, cpl=True)

# Raster Data Source Routines
create_ds = VoidPtrOutput(
    "GDALCreate", argtypes=[c_void_p, c_char_p, c_int, c_int, c_int, c_int, c_void_p]
)
open_ds = VoidPtrOutput("GDALOpen", argtypes=[c_char_p, c_int])
close_ds = VoidOutput("GDALClose", argtypes=[c_void_p], errcheck=False)
flush_ds = IntOutput("GDALFlushCache", argtypes=[c_void_p])
copy_ds = VoidPtrOutput(
    "GDALCreateCopy",
    argtypes=[
        c_void_p,
        c_char_p,
        c_void_p,
        c_int,
        POINTER(c_char_p),
        c_void_p,
        c_void_p,
    ],
)
add_band_ds = VoidOutput("GDALAddBand", argtypes=[c_void_p, c_int])
get_ds_description = ConstStringOutput("GDALGetDescription", argtypes=[c_void_p])
get_ds_driver = VoidPtrOutput("GDALGetDatasetDriver", argtypes=[c_void_p])
get_ds_info = ConstStringOutput("GDALInfo", argtypes=[c_void_p, c_void_p])
get_ds_xsize = IntOutput("GDALGetRasterXSize", argtypes=[c_void_p])
get_ds_ysize = IntOutput("GDALGetRasterYSize", argtypes=[c_void_p])
get_ds_raster_count = IntOutput("GDALGetRasterCount", argtypes=[c_void_p])
get_ds_raster_band = VoidPtrOutput("GDALGetRasterBand", argtypes=[c_void_p, c_int])
get_ds_projection_ref = ConstStringOutput("GDALGetProjectionRef", argtypes=[c_void_p])
set_ds_projection_ref = VoidOutput("GDALSetProjection", argtypes=[c_void_p, c_char_p])
get_ds_geotransform = VoidOutput(
    "GDALGetGeoTransform", argtypes=[c_void_p, POINTER(c_double * 6)], errcheck=False
)
set_ds_geotransform = VoidOutput(
    "GDALSetGeoTransform", argtypes=[c_void_p, POINTER(c_double * 6)]
)

get_ds_metadata = CharArrayOutput(
    "GDALGetMetadata", argtypes=[c_void_p, c_char_p], errcheck=False
)
set_ds_metadata = VoidOutput(
    "GDALSetMetadata", argtypes=[c_void_p, POINTER(c_char_p), c_char_p]
)
get_ds_metadata_domain_list = CharArrayOutput(
    "GDALGetMetadataDomainList", argtypes=[c_void_p], errcheck=False
)
get_ds_metadata_item = ConstStringOutput(
    "GDALGetMetadataItem", argtypes=[c_void_p, c_char_p, c_char_p]
)
set_ds_metadata_item = ConstStringOutput(
    "GDALSetMetadataItem", argtypes=[c_void_p, c_char_p, c_char_p, c_char_p]
)
free_dsl = VoidOutput("CSLDestroy", argtypes=[POINTER(c_char_p)], errcheck=False)

# Raster Band Routines
band_io = VoidOutput(
    "GDALRasterIO",
    argtypes=[
        c_void_p,
        c_int,
        c_int,
        c_int,
        c_int,
        c_int,
        c_void_p,
        c_int,
        c_int,
        c_int,
        c_int,
        c_int,
    ],
)
get_band_xsize = IntOutput("GDALGetRasterBandXSize", argtypes=[c_void_p])
get_band_ysize = IntOutput("GDALGetRasterBandYSize", argtypes=[c_void_p])
get_band_index = IntOutput("GDALGetBandNumber", argtypes=[c_void_p])
get_band_description = ConstStringOutput("GDALGetDescription", argtypes=[c_void_p])
get_band_ds = VoidPtrOutput("GDALGetBandDataset", argtypes=[c_void_p])
get_band_datatype = IntOutput("GDALGetRasterDataType", argtypes=[c_void_p])
get_band_color_interp = IntOutput(
    "GDALGetRasterColorInterpretation", argtypes=[c_void_p]
)
get_band_nodata_value = DoubleOutput(
    "GDALGetRasterNoDataValue", argtypes=[c_void_p, POINTER(c_int)]
)
set_band_nodata_value = VoidOutput(
    "GDALSetRasterNoDataValue", argtypes=[c_void_p, c_double]
)
delete_band_nodata_value = VoidOutput(
    "GDALDeleteRasterNoDataValue", argtypes=[c_void_p]
)
get_band_statistics = VoidOutput(
    "GDALGetRasterStatistics",
    argtypes=[
        c_void_p,
        c_int,
        c_int,
        POINTER(c_double),
        POINTER(c_double),
        POINTER(c_double),
        POINTER(c_double),
        c_void_p,
        c_void_p,
    ],
)
compute_band_statistics = VoidOutput(
    "GDALComputeRasterStatistics",
    argtypes=[
        c_void_p,
        c_int,
        POINTER(c_double),
        POINTER(c_double),
        POINTER(c_double),
        POINTER(c_double),
        c_void_p,
        c_void_p,
    ],
)

# Reprojection routine
reproject_image = VoidOutput(
    "GDALReprojectImage",
    argtypes=[
        c_void_p,
        c_char_p,
        c_void_p,
        c_char_p,
        c_int,
        c_double,
        c_double,
        c_void_p,
        c_void_p,
        c_void_p,
    ],
)
auto_create_warped_vrt = VoidPtrOutput(
    "GDALAutoCreateWarpedVRT",
    argtypes=[c_void_p, c_char_p, c_char_p, c_int, c_double, c_void_p],
)

# Create VSI gdal raster files from in-memory buffers.
# https://gdal.org/api/cpl.html#cpl-vsi-h
create_vsi_file_from_mem_buffer = VoidPtrOutput(
    "VSIFileFromMemBuffer", argtypes=[c_char_p, c_void_p, c_int, c_int]
)
get_mem_buffer_from_vsi_file = VoidPtrOutput(
    "VSIGetMemFileBuffer", argtypes=[c_char_p, POINTER(c_int), c_bool]
)
unlink_vsi_file = IntOutput("VSIUnlink", argtypes=[c_char_p])
