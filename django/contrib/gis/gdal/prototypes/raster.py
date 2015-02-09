"""
This module houses the ctypes function prototypes for GDAL DataSource (raster)
related data structures.
"""
from ctypes import POINTER, c_char_p, c_double, c_int, c_void_p
from functools import partial

from django.contrib.gis.gdal.libgdal import lgdal
from django.contrib.gis.gdal.prototypes.generation import (
    const_string_output, double_output, int_output, void_output,
    voidptr_output,
)

# For more detail about c function names and definitions see
# http://gdal.org/gdal_8h.html
# http://gdal.org/gdalwarper_8h.html

# Prepare partial functions that use cpl error codes
void_output = partial(void_output, cpl=True)
const_string_output = partial(const_string_output, cpl=True)
double_output = partial(double_output, cpl=True)

# Raster Driver Routines
register_all = void_output(lgdal.GDALAllRegister, [])
get_driver = voidptr_output(lgdal.GDALGetDriver, [c_int])
get_driver_by_name = voidptr_output(lgdal.GDALGetDriverByName, [c_char_p], errcheck=False)
get_driver_count = int_output(lgdal.GDALGetDriverCount, [])
get_driver_description = const_string_output(lgdal.GDALGetDescription, [c_void_p])

# Raster Data Source Routines
create_ds = voidptr_output(lgdal.GDALCreate, [c_void_p, c_char_p, c_int, c_int, c_int, c_int])
open_ds = voidptr_output(lgdal.GDALOpen, [c_char_p, c_int])
close_ds = void_output(lgdal.GDALClose, [c_void_p])
copy_ds = voidptr_output(lgdal.GDALCreateCopy, [c_void_p, c_char_p, c_void_p, c_int,
                                                POINTER(c_char_p), c_void_p, c_void_p])
add_band_ds = void_output(lgdal.GDALAddBand, [c_void_p, c_int])
get_ds_description = const_string_output(lgdal.GDALGetDescription, [])
get_ds_driver = voidptr_output(lgdal.GDALGetDatasetDriver, [c_void_p])
get_ds_xsize = int_output(lgdal.GDALGetRasterXSize, [c_void_p])
get_ds_ysize = int_output(lgdal.GDALGetRasterYSize, [c_void_p])
get_ds_raster_count = int_output(lgdal.GDALGetRasterCount, [c_void_p])
get_ds_raster_band = voidptr_output(lgdal.GDALGetRasterBand, [c_void_p, c_int])
get_ds_projection_ref = const_string_output(lgdal.GDALGetProjectionRef, [c_void_p])
set_ds_projection_ref = void_output(lgdal.GDALSetProjection, [c_void_p, c_char_p])
get_ds_geotransform = void_output(lgdal.GDALGetGeoTransform, [c_void_p, POINTER(c_double * 6)], errcheck=False)
set_ds_geotransform = void_output(lgdal.GDALSetGeoTransform, [c_void_p, POINTER(c_double * 6)])

# Raster Band Routines
band_io = void_output(lgdal.GDALRasterIO, [c_void_p, c_int, c_int, c_int, c_int, c_int,
                                           c_void_p, c_int, c_int, c_int, c_int, c_int])
get_band_xsize = int_output(lgdal.GDALGetRasterBandXSize, [c_void_p])
get_band_ysize = int_output(lgdal.GDALGetRasterBandYSize, [c_void_p])
get_band_index = int_output(lgdal.GDALGetBandNumber, [c_void_p])
get_band_description = const_string_output(lgdal.GDALGetDescription, [c_void_p])
get_band_ds = voidptr_output(lgdal.GDALGetBandDataset, [c_void_p])
get_band_datatype = int_output(lgdal.GDALGetRasterDataType, [c_void_p])
get_band_nodata_value = double_output(lgdal.GDALGetRasterNoDataValue, [c_void_p, POINTER(c_int)])
set_band_nodata_value = void_output(lgdal.GDALSetRasterNoDataValue, [c_void_p, c_double])
get_band_minimum = double_output(lgdal.GDALGetRasterMinimum, [c_void_p, POINTER(c_int)])
get_band_maximum = double_output(lgdal.GDALGetRasterMaximum, [c_void_p, POINTER(c_int)])

# Reprojection routine
reproject_image = void_output(lgdal.GDALReprojectImage, [c_void_p, c_char_p, c_void_p, c_char_p,
                                                         c_int, c_double, c_double,
                                                         c_void_p, c_void_p, c_void_p])
