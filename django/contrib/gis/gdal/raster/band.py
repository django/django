from ctypes import byref, c_int

from django.contrib.gis.gdal.base import GDALBase
from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.gdal.prototypes import raster as capi
from django.contrib.gis.shortcuts import numpy
from django.utils import six
from django.utils.encoding import force_text
from django.utils.six.moves import range

from .const import GDAL_INTEGER_TYPES, GDAL_PIXEL_TYPES, GDAL_TO_CTYPES


class GDALBand(GDALBase):
    """
    Wraps a GDAL raster band, needs to be obtained from a GDALRaster object.
    """
    def __init__(self, source, index):
        self.source = source
        self._ptr = capi.get_ds_raster_band(source._ptr, index)

    @property
    def description(self):
        """
        Returns the description string of the band.
        """
        return force_text(capi.get_band_description(self._ptr))

    @property
    def width(self):
        """
        Width (X axis) in pixels of the band.
        """
        return capi.get_band_xsize(self._ptr)

    @property
    def height(self):
        """
        Height (Y axis) in pixels of the band.
        """
        return capi.get_band_ysize(self._ptr)

    @property
    def pixel_count(self):
        """
        Returns the total number of pixels in this band.
        """
        return self.width * self.height

    @property
    def min(self):
        """
        Returns the minimum pixel value for this band.
        """
        return capi.get_band_minimum(self._ptr, byref(c_int()))

    @property
    def max(self):
        """
        Returns the maximum pixel value for this band.
        """
        return capi.get_band_maximum(self._ptr, byref(c_int()))

    @property
    def nodata_value(self):
        """
        Returns the nodata value for this band, or None if it isn't set.
        """
        # Get value and nodata exists flag
        nodata_exists = c_int()
        value = capi.get_band_nodata_value(self._ptr, nodata_exists)
        if not nodata_exists:
            value = None
        # If the pixeltype is an integer, convert to int
        elif self.datatype() in GDAL_INTEGER_TYPES:
            value = int(value)
        return value

    @nodata_value.setter
    def nodata_value(self, value):
        """
        Sets the nodata value for this band.
        """
        if not isinstance(value, (int, float)):
            raise ValueError('Nodata value must be numeric.')
        capi.set_band_nodata_value(self._ptr, value)
        self.source._flush()

    def datatype(self, as_string=False):
        """
        Returns the GDAL Pixel Datatype for this band.
        """
        dtype = capi.get_band_datatype(self._ptr)
        if as_string:
            dtype = GDAL_PIXEL_TYPES[dtype]
        return dtype

    def data(self, data=None, offset=None, size=None, as_memoryview=False):
        """
        Reads or writes pixel values for this band. Blocks of data can
        be accessed by specifying the width, height and offset of the
        desired block. The same specification can be used to update
        parts of a raster by providing an array of values.

        Allowed input data types are bytes, memoryview, list, tuple, and array.
        """
        if not offset:
            offset = (0, 0)

        if not size:
            size = (self.width - offset[0], self.height - offset[1])

        if any(x <= 0 for x in size):
            raise ValueError('Offset too big for this raster.')

        if size[0] > self.width or size[1] > self.height:
            raise ValueError('Size is larger than raster.')

        # Create ctypes type array generator
        ctypes_array = GDAL_TO_CTYPES[self.datatype()] * (size[0] * size[1])

        if data is None:
            # Set read mode
            access_flag = 0
            # Prepare empty ctypes array
            data_array = ctypes_array()
        else:
            # Set write mode
            access_flag = 1

            # Instantiate ctypes array holding the input data
            if isinstance(data, (bytes, six.memoryview)) or (numpy and isinstance(data, numpy.ndarray)):
                data_array = ctypes_array.from_buffer_copy(data)
            else:
                data_array = ctypes_array(*data)

        # Access band
        capi.band_io(self._ptr, access_flag, offset[0], offset[1],
                     size[0], size[1], byref(data_array), size[0],
                     size[1], self.datatype(), 0, 0)

        # Return data as numpy array if possible, otherwise as list
        if data is None:
            if as_memoryview:
                return memoryview(data_array)
            elif numpy:
                return numpy.frombuffer(
                    data_array, dtype=numpy.dtype(data_array)).reshape(size)
            else:
                return list(data_array)
        else:
            self.source._flush()


class BandList(list):
    def __init__(self, source):
        self.source = source
        list.__init__(self)

    def __iter__(self):
        for idx in range(1, len(self) + 1):
            yield GDALBand(self.source, idx)

    def __len__(self):
        return capi.get_ds_raster_count(self.source._ptr)

    def __getitem__(self, index):
        try:
            return GDALBand(self.source, index + 1)
        except GDALException:
            raise GDALException('Unable to get band index %d' % index)
