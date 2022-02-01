"""
This module houses the ctypes function prototypes for GDAL DataSource (raster)
related data structures.
"""
from ctypes import POINTER, c_bool, c_char_p, c_double, c_int, c_void_p
from functools import partial

from django.contrib.gis.gdal.libgdal import std_call
from django.contrib.gis.gdal.prototypes.generation import (
    chararray_output, const_string_output, double_output, int_output,
    void_output, voidptr_output,
)

# For more detail about c function names and definitions see
# https://gdal.org/api/raster_c_api.html
# https://gdal.org/doxygen/gdalwarper_8h.html
# https://gdal.org/api/gdal_utils.html

# Prepare partial functions that use cpl error codes
void_output = partial(void_output, cpl=True)
const_string_output = partial(const_string_output, cpl=True)
double_output = partial(double_output, cpl=True)

# Raster Driver Routines
register_all = void_output(std_call('GDALAllRegister'), [], errcheck=False)
get_driver = voidptr_output(std_call('GDALGetDriver'), [c_int])
get_driver_by_name = voidptr_output(std_call('GDALGetDriverByName'), [c_char_p], errcheck=False)
get_driver_count = int_output(std_call('GDALGetDriverCount'), [])
get_driver_description = const_string_output(std_call('GDALGetDescription'), [c_void_p])

# Raster Data Source Routines
create_ds = voidptr_output(std_call('GDALCreate'), [c_void_p, c_char_p, c_int, c_int, c_int, c_int, c_void_p])
open_ds = voidptr_output(std_call('GDALOpen'), [c_char_p, c_int])
close_ds = void_output(std_call('GDALClose'), [c_void_p], errcheck=False)
flush_ds = int_output(std_call('GDALFlushCache'), [c_void_p])
copy_ds = voidptr_output(
    std_call('GDALCreateCopy'),
    [c_void_p, c_char_p, c_void_p, c_int, POINTER(c_char_p), c_void_p, c_void_p]
)
add_band_ds = void_output(std_call('GDALAddBand'), [c_void_p, c_int])
get_ds_description = const_string_output(std_call('GDALGetDescription'), [c_void_p])
get_ds_driver = voidptr_output(std_call('GDALGetDatasetDriver'), [c_void_p])
get_ds_info = const_string_output(std_call('GDALInfo'), [c_void_p, c_void_p])
get_ds_xsize = int_output(std_call('GDALGetRasterXSize'), [c_void_p])
get_ds_ysize = int_output(std_call('GDALGetRasterYSize'), [c_void_p])
get_ds_raster_count = int_output(std_call('GDALGetRasterCount'), [c_void_p])
get_ds_raster_band = voidptr_output(std_call('GDALGetRasterBand'), [c_void_p, c_int])
get_ds_projection_ref = const_string_output(std_call('GDALGetProjectionRef'), [c_void_p])
set_ds_projection_ref = void_output(std_call('GDALSetProjection'), [c_void_p, c_char_p])
get_ds_geotransform = void_output(std_call('GDALGetGeoTransform'), [c_void_p, POINTER(c_double * 6)], errcheck=False)
set_ds_geotransform = void_output(std_call('GDALSetGeoTransform'), [c_void_p, POINTER(c_double * 6)])

get_ds_metadata = chararray_output(std_call('GDALGetMetadata'), [c_void_p, c_char_p], errcheck=False)
set_ds_metadata = void_output(std_call('GDALSetMetadata'), [c_void_p, POINTER(c_char_p), c_char_p])
get_ds_metadata_domain_list = chararray_output(std_call('GDALGetMetadataDomainList'), [c_void_p], errcheck=False)
get_ds_metadata_item = const_string_output(std_call('GDALGetMetadataItem'), [c_void_p, c_char_p, c_char_p])
set_ds_metadata_item = const_string_output(std_call('GDALSetMetadataItem'), [c_void_p, c_char_p, c_char_p, c_char_p])
free_dsl = void_output(std_call('CSLDestroy'), [POINTER(c_char_p)], errcheck=False)

# Raster Band Routines
band_io = void_output(
    std_call('GDALRasterIO'),
    [c_void_p, c_int, c_int, c_int, c_int, c_int, c_void_p, c_int, c_int, c_int, c_int, c_int]
)
get_band_xsize = int_output(std_call('GDALGetRasterBandXSize'), [c_void_p])
get_band_ysize = int_output(std_call('GDALGetRasterBandYSize'), [c_void_p])
get_band_index = int_output(std_call('GDALGetBandNumber'), [c_void_p])
get_band_description = const_string_output(std_call('GDALGetDescription'), [c_void_p])
get_band_ds = voidptr_output(std_call('GDALGetBandDataset'), [c_void_p])
get_band_datatype = int_output(std_call('GDALGetRasterDataType'), [c_void_p])
get_band_color_interp = int_output(std_call('GDALGetRasterColorInterpretation'), [c_void_p])
get_band_nodata_value = double_output(std_call('GDALGetRasterNoDataValue'), [c_void_p, POINTER(c_int)])
set_band_nodata_value = void_output(std_call('GDALSetRasterNoDataValue'), [c_void_p, c_double])
delete_band_nodata_value = void_output(std_call('GDALDeleteRasterNoDataValue'), [c_void_p])
get_band_statistics = void_output(
    std_call('GDALGetRasterStatistics'),
    [
        c_void_p, c_int, c_int, POINTER(c_double), POINTER(c_double),
        POINTER(c_double), POINTER(c_double), c_void_p, c_void_p,
    ],
)
compute_band_statistics = void_output(
    std_call('GDALComputeRasterStatistics'),
    [c_void_p, c_int, POINTER(c_double), POINTER(c_double), POINTER(c_double), POINTER(c_double), c_void_p, c_void_p],
)

# Reprojection routine
reproject_image = void_output(
    std_call('GDALReprojectImage'),
    [c_void_p, c_char_p, c_void_p, c_char_p, c_int, c_double, c_double, c_void_p, c_void_p, c_void_p]
)
auto_create_warped_vrt = voidptr_output(
    std_call('GDALAutoCreateWarpedVRT'),
    [c_void_p, c_char_p, c_char_p, c_int, c_double, c_void_p]
)

# Create VSI gdal raster files from in-memory buffers.
# https://gdal.org/api/cpl.html#cpl-vsi-h
create_vsi_file_from_mem_buffer = voidptr_output(std_call('VSIFileFromMemBuffer'), [c_char_p, c_void_p, c_int, c_int])
get_mem_buffer_from_vsi_file = voidptr_output(std_call('VSIGetMemFileBuffer'), [c_char_p, POINTER(c_int), c_bool])
unlink_vsi_file = int_output(std_call('VSIUnlink'), [c_char_p])
