from ctypes import byref, c_int

from django.contrib.gis.gdal.base import GDALBase
from django.contrib.gis.gdal.prototypes import raster as capi
from django.utils.encoding import force_text

from .const import GDAL_PIXEL_TYPES


class GDALBand(GDALBase):
    """
    Wraps a GDAL raster band, needs to be obtained from a GDALRaster object.
    """
    def __init__(self, source, index):
        self.source = source
        self.ptr = capi.get_ds_raster_band(source.ptr, index)

    @property
    def description(self):
        """
        Returns the description string of the band.
        """
        return force_text(capi.get_band_description(self.ptr))

    @property
    def width(self):
        """
        Width (X axis) in pixels of the band.
        """
        return capi.get_band_xsize(self.ptr)

    @property
    def height(self):
        """
        Height (Y axis) in pixels of the band.
        """
        return capi.get_band_ysize(self.ptr)

    def datatype(self, as_string=False):
        """
        Returns the GDAL Pixel Datatype for this band.
        """
        dtype = capi.get_band_datatype(self.ptr)
        if as_string:
            dtype = GDAL_PIXEL_TYPES[dtype]
        return dtype

    @property
    def min(self):
        """
        Returns the minimum pixel value for this band.
        """
        return capi.get_band_minimum(self.ptr, byref(c_int()))

    @property
    def max(self):
        """
        Returns the maximum pixel value for this band.
        """
        return capi.get_band_maximum(self.ptr, byref(c_int()))

    @property
    def nodata_value(self):
        """
        Returns the nodata value for this band, or None if it isn't set.
        """
        nodata_exists = c_int()
        value = capi.get_band_nodata_value(self.ptr, nodata_exists)
        return value if nodata_exists else None
