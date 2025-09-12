from ctypes import c_void_p

from django.contrib.gis.gdal.base import GDALBase
from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.gdal.libgdal import GDAL_VERSION
from django.contrib.gis.gdal.prototypes import ds as capi
from django.utils.encoding import force_bytes, force_str


class Driver(GDALBase):
    """
    Wrap a GDAL/OGR Data Source Driver.
    For more information, see the C API documentation:
    https://gdal.org/api/vector_c_api.html
    https://gdal.org/api/raster_c_api.html
    """

    # Case-insensitive aliases for some GDAL/OGR Drivers.
    # For a complete list of original driver names see
    # https://gdal.org/drivers/vector/
    # https://gdal.org/drivers/raster/
    _alias = {
        # vector
        "esri": "ESRI Shapefile",
        "shp": "ESRI Shapefile",
        "shape": "ESRI Shapefile",
        # raster
        "tiff": "GTiff",
        "tif": "GTiff",
        "jpeg": "JPEG",
        "jpg": "JPEG",
    }

    if GDAL_VERSION[:2] <= (3, 10):
        _alias.update(
            {
                "tiger": "TIGER",
                "tiger/line": "TIGER",
            }
        )

    def __init__(self, dr_input):
        """
        Initialize an GDAL/OGR driver on either a string or integer input.
        """
        if isinstance(dr_input, str):
            # If a string name of the driver was passed in
            self.ensure_registered()

            # Checking the alias dictionary (case-insensitive) to see if an
            # alias exists for the given driver.
            if dr_input.lower() in self._alias:
                name = self._alias[dr_input.lower()]
            else:
                name = dr_input

            # Attempting to get the GDAL/OGR driver by the string name.
            driver = c_void_p(capi.get_driver_by_name(force_bytes(name)))
        elif isinstance(dr_input, int):
            self.ensure_registered()
            driver = capi.get_driver(dr_input)
        elif isinstance(dr_input, c_void_p):
            driver = dr_input
        else:
            raise GDALException(
                "Unrecognized input type for GDAL/OGR Driver: %s" % type(dr_input)
            )

        # Making sure we get a valid pointer to the OGR Driver
        if not driver:
            raise GDALException(
                "Could not initialize GDAL/OGR Driver on input: %s" % dr_input
            )
        self.ptr = driver

    def __str__(self):
        return self.name

    @classmethod
    def ensure_registered(cls):
        """
        Attempt to register all the data source drivers.
        """
        # Only register all if the driver count is 0 (or else all drivers will
        # be registered over and over again).
        if not capi.get_driver_count():
            capi.register_all()

    @classmethod
    def driver_count(cls):
        """
        Return the number of GDAL/OGR data source drivers registered.
        """
        return capi.get_driver_count()

    @property
    def name(self):
        """
        Return description/name string for this driver.
        """
        return force_str(capi.get_driver_description(self.ptr))
