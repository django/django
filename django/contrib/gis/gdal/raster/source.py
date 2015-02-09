import os
from ctypes import addressof, byref, c_double

from django.contrib.gis.gdal.base import GDALBase
from django.contrib.gis.gdal.driver import Driver
from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.gdal.prototypes import raster as capi
from django.contrib.gis.gdal.raster.band import GDALBand
from django.contrib.gis.gdal.srs import SpatialReference, SRSException
from django.utils import six
from django.utils.encoding import (
    force_bytes, force_text, python_2_unicode_compatible,
)
from django.utils.functional import cached_property
from django.utils.six.moves import range


class TransformPoint(list):
    indices = {
        'origin': (0, 3),
        'scale': (1, 5),
        'skew': (2, 4),
    }

    def __init__(self, raster, prop):
        x = raster.geotransform[self.indices[prop][0]]
        y = raster.geotransform[self.indices[prop][1]]
        list.__init__(self, [x, y])
        self._raster = raster
        self._prop = prop

    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]


@python_2_unicode_compatible
class GDALRaster(GDALBase):
    """
    Wraps a raster GDAL Data Source object.
    """
    def __init__(self, ds_input, write=False):
        self._write = 1 if write else 0
        Driver.ensure_registered()

        # If input is a valid file path, try setting file as source.
        if isinstance(ds_input, six.string_types):
            if os.path.exists(ds_input):
                try:
                    # GDALOpen will auto-detect the data source type.
                    self.ptr = capi.open_ds(force_bytes(ds_input), self._write)
                except GDALException as err:
                    raise GDALException('Could not open the datasource at "{}" ({}).'.format(
                        ds_input, err))
            else:
                raise GDALException('Unable to read raster source input "{}"'.format(ds_input))
        else:
            raise GDALException('Invalid data source input type: "{}".'.format(type(ds_input)))

    def __del__(self):
        if self._ptr and capi:
            capi.close_ds(self._ptr)

    def __str__(self):
        return self.name

    def __repr__(self):
        """
        Short-hand representation because WKB may be very large.
        """
        return '<Raster object at %s>' % hex(addressof(self.ptr))

    @property
    def name(self):
        return force_text(capi.get_ds_description(self.ptr))

    @cached_property
    def driver(self):
        ds_driver = capi.get_ds_driver(self.ptr)
        return Driver(ds_driver)

    @property
    def width(self):
        """
        Width (X axis) in pixels.
        """
        return capi.get_ds_xsize(self.ptr)

    @property
    def height(self):
        """
        Height (Y axis) in pixels.
        """
        return capi.get_ds_ysize(self.ptr)

    @property
    def srs(self):
        """
        Returns the Spatial Reference used in this GDALRaster.
        """
        try:
            wkt = capi.get_ds_projection_ref(self.ptr)
            return SpatialReference(wkt, srs_type='wkt')
        except SRSException:
            return None

    @cached_property
    def geotransform(self):
        """
        Returns the geotransform of the data source.
        Returns the default geotransform if it does not exist or has not been
        set previously. The default is (0.0, 1.0, 0.0, 0.0, 0.0, -1.0).
        """
        # Create empty ctypes double array for data
        gtf = (c_double * 6)()
        capi.get_ds_geotransform(self.ptr, byref(gtf))
        return tuple(gtf)

    @property
    def origin(self):
        return TransformPoint(self, 'origin')

    @property
    def scale(self):
        return TransformPoint(self, 'scale')

    @property
    def skew(self):
        return TransformPoint(self, 'skew')

    @property
    def extent(self):
        """
        Returns the extent as a 4-tuple (xmin, ymin, xmax, ymax).
        """
        # Calculate boundary values based on scale and size
        xval = self.origin.x + self.scale.x * self.width
        yval = self.origin.y + self.scale.y * self.height
        # Calculate min and max values
        xmin = min(xval, self.origin.x)
        xmax = max(xval, self.origin.x)
        ymin = min(yval, self.origin.y)
        ymax = max(yval, self.origin.y)

        return xmin, ymin, xmax, ymax

    @cached_property
    def bands(self):
        bands = []
        for idx in range(1, capi.get_ds_raster_count(self.ptr) + 1):
            bands.append(GDALBand(self, idx))
        return bands
