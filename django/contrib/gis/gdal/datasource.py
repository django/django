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
# ctypes prerequisites.
from ctypes import byref

# The GDAL C library, OGR exceptions, and the Layer object.
from django.contrib.gis.gdal.base import GDALBase
from django.contrib.gis.gdal.driver import Driver
from django.contrib.gis.gdal.error import OGRException, OGRIndexError
from django.contrib.gis.gdal.layer import Layer

# Getting the ctypes prototypes for the DataSource.
from django.contrib.gis.gdal.prototypes import ds as capi

# For more information, see the OGR C API source code:
#  http://www.gdal.org/ogr/ogr__api_8h.html
#
# The OGR_DS_* routines are relevant here.
class DataSource(GDALBase):
    "Wraps an OGR Data Source object."

    #### Python 'magic' routines ####
    def __init__(self, ds_input, ds_driver=False, write=False):
        # The write flag.
        if write:
            self._write = 1
        else:
            self._write = 0

        # Registering all the drivers, this needs to be done
        #  _before_ we try to open up a data source.
        if not capi.get_driver_count():
            capi.register_all()

        if isinstance(ds_input, basestring):
            # The data source driver is a void pointer.
            ds_driver = Driver.ptr_type()
            try:
                # OGROpen will auto-detect the data source type.
                ds = capi.open_ds(ds_input, self._write, byref(ds_driver))
            except OGRException:
                # Making the error message more clear rather than something
                # like "Invalid pointer returned from OGROpen".
                raise OGRException('Could not open the datasource at "%s"' % ds_input)
        elif isinstance(ds_input, self.ptr_type) and isinstance(ds_driver, Driver.ptr_type):
            ds = ds_input
        else:
            raise OGRException('Invalid data source input type: %s' % type(ds_input))

        if bool(ds):
            self.ptr = ds
            self.driver = Driver(ds_driver)
        else:
            # Raise an exception if the returned pointer is NULL 
            raise OGRException('Invalid data source file "%s"' % ds_input)

    def __del__(self):
        "Destroys this DataStructure object."
        if self._ptr: capi.destroy_ds(self._ptr)

    def __iter__(self):
        "Allows for iteration over the layers in a data source."
        for i in xrange(self.layer_count):
            yield self[i]

    def __getitem__(self, index):
        "Allows use of the index [] operator to get a layer at the index."
        if isinstance(index, basestring):
            l = capi.get_layer_by_name(self.ptr, index)
            if not l: raise OGRIndexError('invalid OGR Layer name given: "%s"' % index)
        elif isinstance(index, int):
            if index < 0 or index >= self.layer_count:
                raise OGRIndexError('index out of range')
            l = capi.get_layer(self._ptr, index)
        else:
            raise TypeError('Invalid index type: %s' % type(index))
        return Layer(l, self)
        
    def __len__(self):
        "Returns the number of layers within the data source."
        return self.layer_count

    def __str__(self):
        "Returns OGR GetName and Driver for the Data Source."
        return '%s (%s)' % (self.name, str(self.driver))

    @property
    def layer_count(self):
        "Returns the number of layers in the data source."
        return capi.get_layer_count(self._ptr)

    @property
    def name(self):
        "Returns the name of the data source."
        return capi.get_ds_name(self._ptr)
