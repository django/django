# types and ctypes
from types import StringType
from ctypes import c_char_p, c_int, c_void_p, byref, string_at

# The GDAL C library, OGR exceptions, and the Layer object.
from django.contrib.gis.gdal.libgdal import lgdal
from django.contrib.gis.gdal.OGRError import OGRException, check_err
from django.contrib.gis.gdal.Layer import Layer

"""
  DataSource is a wrapper for the OGR Data Source object, which provides
   an interface for reading vector geometry data from many different file
   formats (including ESRI shapefiles).

  Example:
    ds = DataSource('/home/foo/bar.shp')
    for layer in ds:
        for feature in layer:
            # Getting the geometry for the feature.
            g = feature.geom

            # Getting the 'description' field for the feature.
            desc = feature['description']

  More documentation forthcoming.
"""

# For more information, see the OGR C API source code:
#  http://www.gdal.org/ogr/ogr__api_8h.html
#
# The OGR_DS* routines are relevant here.

class DataSource(object):
    "Wraps an OGR Data Source object."

    _ds = 0 # Initially NULL
    
    #### Python 'magic' routines ####
    def __init__(self, ds_file):

        # Registering all the drivers, this needs to be done
        #  _before_ we try to open up a data source.
        if not lgdal.OGRRegisterAll():
            raise OGRException, 'Could not register all data source drivers!'

        # The data source driver is a void pointer.
        ds_driver = c_void_p()

        # OGROpen will auto-detect the data source type.
        ds = lgdal.OGROpen(c_char_p(ds_file), c_int(0), byref(ds_driver))

        # Raise an exception if the returned pointer is NULL
        if not ds:
            self._ds = False
            raise OGRException, 'Invalid data source file "%s"' % ds_file
        else:
            self._ds = ds
            self._driver = ds_driver

    def __del__(self):
        "This releases the reference to the data source (destroying it if it's the only one)."
        if self._ds: lgdal.OGRReleaseDataSource(self._ds)

    def __iter__(self):
        "Allows for iteration over the layers in a data source."
        for i in xrange(self.layer_count):
            yield self.__getitem__(i)

    def __getitem__(self, index):
        "Allows use of the index [] operator to get a layer at the index."
        if isinstance(index, StringType):
            l = lgdal.OGR_DS_GetLayerByName(self._ds, c_char_p(index))
            if not l: raise IndexError, 'invalid OGR Layer name given: "%s"' % index
        else:
            if index < 0 or index >= self.layer_count:
                raise IndexError, 'index out of range'
            l = lgdal.OGR_DS_GetLayer(self._ds, c_int(index))
        return Layer(l)
        
    def __len__(self):
        "Returns the number of layers within the data source."
        return self.layer_count

    def __str__(self):
        "Returns OGR GetName and Driver for the Data Source."
        return '%s (%s)' % (self.name, self.driver)

    #### DataSource Properties ####
    @property
    def driver(self):
        "Returns the name of the data source driver."
        return string_at(lgdal.OGR_Dr_GetName(self._driver))
        
    @property
    def layer_count(self):
        "Returns the number of layers in the data source."
        return lgdal.OGR_DS_GetLayerCount(self._ds)

    @property
    def name(self):
        "Returns the name of the data source."
        return string_at(lgdal.OGR_DS_GetName(self._ds))

