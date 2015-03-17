import json
import os
from ctypes import addressof, byref, c_double

from django.contrib.gis.gdal.base import GDALBase
from django.contrib.gis.gdal.driver import Driver
from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.gdal.prototypes import raster as capi
from django.contrib.gis.gdal.raster.band import GDALBand
from django.contrib.gis.gdal.srs import SpatialReference, SRSException
from django.contrib.gis.geometry.regex import json_regex
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

    @x.setter
    def x(self, value):
        gtf = self._raster.geotransform
        gtf[self.indices[self._prop][0]] = value
        self._raster.geotransform = gtf

    @property
    def y(self):
        return self[1]

    @y.setter
    def y(self, value):
        gtf = self._raster.geotransform
        gtf[self.indices[self._prop][1]] = value
        self._raster.geotransform = gtf


@python_2_unicode_compatible
class GDALRaster(GDALBase):
    """
    Wraps a raster GDAL Data Source object.
    """
    def __init__(self, ds_input, write=False):
        self._write = 1 if write else 0
        Driver.ensure_registered()

        # Preprocess json inputs. This converts json strings to dictionaries,
        # which are parsed below the same way as direct dictionary inputs.
        if isinstance(ds_input, six.string_types) and json_regex.match(ds_input):
            ds_input = json.loads(ds_input)

        # If input is a valid file path, try setting file as source.
        if isinstance(ds_input, six.string_types):
            if not os.path.exists(ds_input):
                raise GDALException('Unable to read raster source input "{}"'.format(ds_input))
            try:
                # GDALOpen will auto-detect the data source type.
                self._ptr = capi.open_ds(force_bytes(ds_input), self._write)
            except GDALException as err:
                raise GDALException('Could not open the datasource at "{}" ({}).'.format(ds_input, err))
        elif isinstance(ds_input, dict):
            # A new raster needs to be created in write mode
            self._write = 1

            # Create driver (in memory by default)
            driver = Driver(ds_input.get('driver', 'MEM'))

            # For out of memory drivers, check filename argument
            if driver.name != 'MEM' and 'name' not in ds_input:
                raise GDALException('Specify name for creation of raster with driver "{}".'.format(driver.name))

            # Check if width and height where specified
            if 'width' not in ds_input or 'height' not in ds_input:
                raise GDALException('Specify width and height attributes for JSON or dict input.')

            # Check if srid was specified
            if 'srid' not in ds_input:
                raise GDALException('Specify srid for JSON or dict input.')

            # Create GDAL Raster
            self._ptr = capi.create_ds(
                driver._ptr,
                force_bytes(ds_input.get('name', '')),
                ds_input['width'],
                ds_input['height'],
                ds_input.get('nr_of_bands', len(ds_input.get('bands', []))),
                ds_input.get('datatype', 6),
                None
            )

            # Set band data if provided
            for i, band_input in enumerate(ds_input.get('bands', [])):
                self.bands[i].data(band_input['data'])
                if 'nodata_value' in band_input:
                    self.bands[i].nodata_value = band_input['nodata_value']

            # Set SRID, default to 0 (this assures SRS is always instanciated)
            self.srs = ds_input.get('srid')

            # Set additional properties if provided
            if 'origin' in ds_input:
                self.origin.x, self.origin.y = ds_input['origin']

            if 'scale' in ds_input:
                self.scale.x, self.scale.y = ds_input['scale']

            if 'skew' in ds_input:
                self.skew.x, self.skew.y = ds_input['skew']
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
        return '<Raster object at %s>' % hex(addressof(self._ptr))

    def _flush(self):
        """
        Flush all data from memory into the source file if it exists.
        The data that needs flushing are geotransforms, coordinate systems,
        nodata_values and pixel values. This function will be called
        automatically wherever it is needed.
        """
        # Raise an Exception if the value is being changed in read mode.
        if not self._write:
            raise GDALException('Raster needs to be opened in write mode to change values.')
        capi.flush_ds(self._ptr)

    @property
    def name(self):
        """
        Returns the name of this raster. Corresponds to filename
        for file-based rasters.
        """
        return force_text(capi.get_ds_description(self._ptr))

    @cached_property
    def driver(self):
        """
        Returns the GDAL Driver used for this raster.
        """
        ds_driver = capi.get_ds_driver(self._ptr)
        return Driver(ds_driver)

    @property
    def width(self):
        """
        Width (X axis) in pixels.
        """
        return capi.get_ds_xsize(self._ptr)

    @property
    def height(self):
        """
        Height (Y axis) in pixels.
        """
        return capi.get_ds_ysize(self._ptr)

    @property
    def srs(self):
        """
        Returns the SpatialReference used in this GDALRaster.
        """
        try:
            wkt = capi.get_ds_projection_ref(self._ptr)
            if not wkt:
                return None
            return SpatialReference(wkt, srs_type='wkt')
        except SRSException:
            return None

    @srs.setter
    def srs(self, value):
        """
        Sets the spatial reference used in this GDALRaster. The input can be
        a SpatialReference or any parameter accepted by the SpatialReference
        constructor.
        """
        if isinstance(value, SpatialReference):
            srs = value
        elif isinstance(value, six.integer_types + six.string_types):
            srs = SpatialReference(value)
        else:
            raise ValueError('Could not create a SpatialReference from input.')
        capi.set_ds_projection_ref(self._ptr, srs.wkt.encode())
        self._flush()

    @property
    def geotransform(self):
        """
        Returns the geotransform of the data source.
        Returns the default geotransform if it does not exist or has not been
        set previously. The default is [0.0, 1.0, 0.0, 0.0, 0.0, -1.0].
        """
        # Create empty ctypes double array for data
        gtf = (c_double * 6)()
        capi.get_ds_geotransform(self._ptr, byref(gtf))
        return list(gtf)

    @geotransform.setter
    def geotransform(self, values):
        "Sets the geotransform for the data source."
        if sum([isinstance(x, (int, float)) for x in values]) != 6:
            raise ValueError('Geotransform must consist of 6 numeric values.')
        # Create ctypes double array with input and write data
        values = (c_double * 6)(*values)
        capi.set_ds_geotransform(self._ptr, byref(values))
        self._flush()

    @property
    def origin(self):
        """
        Coordinates of the raster origin.
        """
        return TransformPoint(self, 'origin')

    @property
    def scale(self):
        """
        Pixel scale in units of the raster projection.
        """
        return TransformPoint(self, 'scale')

    @property
    def skew(self):
        """
        Skew of pixels (rotation parameters).
        """
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
        """
        Returns the bands of this raster as a list of GDALBand instances.
        """
        bands = []
        for idx in range(1, capi.get_ds_raster_count(self._ptr) + 1):
            bands.append(GDALBand(self, idx))
        return bands
