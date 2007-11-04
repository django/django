# types and ctypes
from types import StringType
from ctypes import c_char_p, c_int, c_void_p, byref, string_at

# The GDAL C library, OGR exceptions, and the Layer object.
from django.contrib.gis.gdal.libgdal import lgdal
from django.contrib.gis.gdal.error import OGRException

# For more information, see the OGR C API source code:
#  http://www.gdal.org/ogr/ogr__api_8h.html
#
# The OGR_Dr_* routines are relevant here.

class Driver(object):
    "Wraps an OGR Data Source Driver."

    # Case-insensitive aliases for OGR Drivers.
    _alias = {'esri' : 'ESRI Shapefile',
              'shp' : 'ESRI Shapefile',
              'shape' : 'ESRI Shapefile',
              'tiger' : 'TIGER',
              'tiger/line' : 'TIGER',
              }
                
    def __init__(self, input, ptr=False):
        "Initializes an OGR driver on either a string or integer input."

        if isinstance(input, StringType):
            # If a string name of the driver was passed in
            self._dr = None # Initially NULL
            self._register()

            # Checking the alias dictionary (case-insensitive) to see if an alias
            #  exists for the given driver.
            if input.lower() in self._alias:
                name = c_char_p(self._alias[input.lower()])
            else:
                name = c_char_p(input)

            # Attempting to get the OGR driver by the string name.
            dr = lgdal.OGRGetDriverByName(name)
        elif isinstance(input, int):
            self._register()
            dr = lgdal.OGRGetDriver(c_int(input))
        elif isinstance(input, c_void_p):
            dr = input
        else:
            raise OGRException('Unrecognized input type for OGR Driver: %s' % str(type(input)))

        # Making sure we get a valid pointer to the OGR Driver
        if not dr:
            raise OGRException('Could not initialize OGR Driver on input: %s' % str(input))
        self._dr = dr

    def __str__(self):
        "Returns the string name of the OGR Driver."
        return string_at(lgdal.OGR_Dr_GetName(self._dr))

    def _register(self):
        "Attempts to register all the data source drivers."
        # Only register all if the driver count is 0 (or else all drivers
        #  will be registered over and over again)
        if not self.driver_count and not lgdal.OGRRegisterAll():
            raise OGRException('Could not register all the OGR data source drivers!')
                    
    # Driver properties
    @property
    def driver_count(self):
        "Returns the number of OGR data source drivers registered."
        return lgdal.OGRGetDriverCount()
    
    def create_ds(self, **kwargs):
        "Creates a data source using the keyword args as name value options."
        raise NotImplementedError
        # Getting the options string
        #options = ''
        #n_opts = len(kwargs)
        #for i in xrange(n_opts):
        #    options += '%s=%s' % (str(k), str(v))
        #    if i < n_opts-1: options += ','
        #opts = c_char_p(options)
        
        
        
    
