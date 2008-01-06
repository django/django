# prerequisites imports 
from ctypes import c_void_p
from django.contrib.gis.gdal.error import OGRException
from django.contrib.gis.gdal.prototypes.ds import \
    get_driver, get_driver_by_name, get_driver_count, get_driver_name, register_all

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
                
    def __init__(self, dr_input):
        "Initializes an OGR driver on either a string or integer input."

        if isinstance(dr_input, basestring):
            # If a string name of the driver was passed in
            self._ptr = None # Initially NULL
            self._register()

            # Checking the alias dictionary (case-insensitive) to see if an alias
            #  exists for the given driver.
            if dr_input.lower() in self._alias:
                name = self._alias[dr_input.lower()]
            else:
                name = dr_input

            # Attempting to get the OGR driver by the string name.
            dr = get_driver_by_name(name)
        elif isinstance(dr_input, int):
            self._register()
            dr = get_driver(dr_input)
        elif isinstance(dr_input, c_void_p):
            dr = dr_input
        else:
            raise OGRException('Unrecognized input type for OGR Driver: %s' % str(type(dr_input)))

        # Making sure we get a valid pointer to the OGR Driver
        if not dr:
            raise OGRException('Could not initialize OGR Driver on input: %s' % str(dr_input))
        self._ptr = dr

    def __str__(self):
        "Returns the string name of the OGR Driver."
        return get_driver_name(self._ptr)

    def _register(self):
        "Attempts to register all the data source drivers."
        # Only register all if the driver count is 0 (or else all drivers
        # will be registered over and over again)
        if not self.driver_count: register_all()
                    
    # Driver properties
    @property
    def driver_count(self):
        "Returns the number of OGR data source drivers registered."
        return get_driver_count()
