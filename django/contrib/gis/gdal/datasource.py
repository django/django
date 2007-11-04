# types and ctypes
from types import StringType
from ctypes import c_char_p, c_int, c_void_p, byref, string_at

# The GDAL C library, OGR exceptions, and the Layer object.
from django.contrib.gis.gdal.libgdal import lgdal
from django.contrib.gis.gdal.error import OGRException, OGRIndexError, check_err
from django.contrib.gis.gdal.layer import Layer
from django.contrib.gis.gdal.driver import Driver

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

# For more information, see the OGR C API source code:
#  http://www.gdal.org/ogr/ogr__api_8h.html
#
# The OGR_DS_* routines are relevant here.

class DataSource(object):
    "Wraps an OGR Data Source object."

    #### Python 'magic' routines ####
    def __init__(self, ds_input, ds_driver=False):

        self._ds = None # Initially NULL

        # Registering all the drivers, this needs to be done
        #  _before_ we try to open up a data source.
        if not lgdal.OGRGetDriverCount() and not lgdal.OGRRegisterAll():
            raise OGRException('Could not register all the OGR data source drivers!')

        if isinstance(ds_input, StringType):

            # The data source driver is a void pointer.
            ds_driver = c_void_p()

            # OGROpen will auto-detect the data source type.
            ds = lgdal.OGROpen(c_char_p(ds_input), c_int(0), byref(ds_driver))
        elif isinstance(ds_input, c_void_p) and isinstance(ds_driver, c_void_p):
            ds = ds_input
        else:
            raise OGRException('Invalid data source input type: %s' % str(type(ds_input)))

        # Raise an exception if the returned pointer is NULL
        if not ds:
            self._ds = False
            raise OGRException('Invalid data source file "%s"' % ds_input)
        else:
            self._ds = ds
            self._driver = Driver(ds_driver)

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
            if not l: raise OGRIndexError('invalid OGR Layer name given: "%s"' % index)
        else:
            if index < 0 or index >= self.layer_count:
                raise OGRIndexError('index out of range')
            l = lgdal.OGR_DS_GetLayer(self._ds, c_int(index))
        return Layer(l)
        
    def __len__(self):
        "Returns the number of layers within the data source."
        return self.layer_count

    def __str__(self):
        "Returns OGR GetName and Driver for the Data Source."
        return '%s (%s)' % (self.name, str(self.driver))

    #### DataSource Properties ####
    @property
    def driver(self):
        "Returns the Driver object for this Data Source."
        return self._driver
        
    @property
    def layer_count(self):
        "Returns the number of layers in the data source."
        return lgdal.OGR_DS_GetLayerCount(self._ds)

    @property
    def name(self):
        "Returns the name of the data source."
        return string_at(lgdal.OGR_DS_GetName(self._ds))

