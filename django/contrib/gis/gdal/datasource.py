"""
 DataSource is a wrapper for the OGR Data Source object, which provides
 an interface for reading vector geometry data from many different file
 formats (including ESRI shapefiles).

 When instantiating a DataSource object, use the filename of a
 GDAL-supported data source.  For example, a SHP file or a
 TIGER/Line file from the government.

 The ds_driver keyword is used internally when a ctypes pointer
 is passed in directly.

 Example:
  ds = DataSource('/home/foo/bar.shp')
  for layer in ds:
      for feature in layer:
          # Getting the geometry for the feature.
          g = feature.geom

          # Getting the 'description' field for the feature.
          desc = feature['description']

          # We can also increment through all of the fields
          #  attached to this feature.
          for field in feature:
              # Get the name of the field (e.g. 'description')
              nm = field.name

              # Get the type (integer) of the field, e.g. 0 => OFTInteger
              t = field.type

              # Returns the value the field; OFTIntegers return ints,
              #  OFTReal returns floats, all else returns string.
              val = field.value
"""
from ctypes import byref
from pathlib import Path

from django.contrib.gis.gdal.base import GDALBase
from django.contrib.gis.gdal.driver import Driver
from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.gdal.layer import Layer
from django.contrib.gis.gdal.prototypes import ds as capi
from django.utils.encoding import force_bytes, force_str


# For more information, see the OGR C API documentation:
#  https://gdal.org/api/vector_c_api.html
#
# The OGR_DS_* routines are relevant here.
class DataSource(GDALBase):
    "Wraps an OGR Data Source object."
    destructor = capi.destroy_ds

    def __init__(self, ds_input, ds_driver=False, write=False, encoding="utf-8"):
        # The write flag.
        if write:
            self._write = 1
        else:
            self._write = 0
        # See also https://trac.osgeo.org/gdal/wiki/rfc23_ogr_unicode
        self.encoding = encoding

        Driver.ensure_registered()

        if isinstance(ds_input, (str, Path)):
            # The data source driver is a void pointer.
            ds_driver = Driver.ptr_type()
            try:
                # OGROpen will auto-detect the data source type.
                ds = capi.open_ds(force_bytes(ds_input), self._write, byref(ds_driver))
            except GDALException:
                # Making the error message more clear rather than something
                # like "Invalid pointer returned from OGROpen".
                raise GDALException('Could not open the datasource at "%s"' % ds_input)
        elif isinstance(ds_input, self.ptr_type) and isinstance(
            ds_driver, Driver.ptr_type
        ):
            ds = ds_input
        else:
            raise GDALException("Invalid data source input type: %s" % type(ds_input))

        if ds:
            self.ptr = ds
            self.driver = Driver(ds_driver)
        else:
            # Raise an exception if the returned pointer is NULL
            raise GDALException('Invalid data source file "%s"' % ds_input)

    def __getitem__(self, index):
        "Allows use of the index [] operator to get a layer at the index."
        if isinstance(index, str):
            try:
                layer = capi.get_layer_by_name(self.ptr, force_bytes(index))
            except GDALException:
                raise IndexError("Invalid OGR layer name given: %s." % index)
        elif isinstance(index, int):
            if 0 <= index < self.layer_count:
                layer = capi.get_layer(self._ptr, index)
            else:
                raise IndexError(
                    "Index out of range when accessing layers in a datasource: %s."
                    % index
                )
        else:
            raise TypeError("Invalid index type: %s" % type(index))
        return Layer(layer, self)

    def __len__(self):
        "Return the number of layers within the data source."
        return self.layer_count

    def __str__(self):
        "Return OGR GetName and Driver for the Data Source."
        return "%s (%s)" % (self.name, self.driver)

    @property
    def layer_count(self):
        "Return the number of layers in the data source."
        return capi.get_layer_count(self._ptr)

    @property
    def name(self):
        "Return the name of the data source."
        name = capi.get_ds_name(self._ptr)
        return force_str(name, self.encoding, strings_only=True)
