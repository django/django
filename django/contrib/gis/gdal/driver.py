from ctypes import c_void_p

from django.contrib.gis.gdal.base import GDALBase
from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.gdal.prototypes import ds as vcapi, raster as rcapi
from django.utils.encoding import force_bytes, force_text


class Driver(GDALBase):
    """
    Wraps a GDAL/OGR Data Source Driver.
    For more information, see the C API source code:
    http://www.gdal.org/gdal_8h.html - http://www.gdal.org/ogr__api_8h.html
    """

    # Case-insensitive aliases for some GDAL/OGR Drivers.
    # For a complete list of original driver names see
    # http://www.gdal.org/ogr_formats.html (vector)
    # http://www.gdal.org/formats_list.html (raster)
    _alias = {
        # vector
        'esri': 'ESRI Shapefile',
        'shp': 'ESRI Shapefile',
        'shape': 'ESRI Shapefile',
        'tiger': 'TIGER',
        'tiger/line': 'TIGER',
        # raster
        'tiff': 'GTiff',
        'tif': 'GTiff',
        'jpeg': 'JPEG',
        'jpg': 'JPEG',
    }

    def __init__(self, dr_input):
        """
        Initializes an GDAL/OGR driver on either a string or integer input.
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
            for iface in (vcapi, rcapi):
                driver = c_void_p(iface.get_driver_by_name(force_bytes(name)))
                if driver:
                    break
        elif isinstance(dr_input, int):
            self.ensure_registered()
            for iface in (vcapi, rcapi):
                driver = iface.get_driver(dr_input)
                if driver:
                    break
        elif isinstance(dr_input, c_void_p):
            driver = dr_input
        else:
            raise GDALException('Unrecognized input type for GDAL/OGR Driver: %s' % type(dr_input))

        # Making sure we get a valid pointer to the OGR Driver
        if not driver:
            raise GDALException('Could not initialize GDAL/OGR Driver on input: %s' % dr_input)
        self.ptr = driver

    def __str__(self):
        return self.name

    @classmethod
    def ensure_registered(cls):
        """
        Attempts to register all the data source drivers.
        """
        # Only register all if the driver counts are 0 (or else all drivers
        # will be registered over and over again)
        if not vcapi.get_driver_count():
            vcapi.register_all()
        if not rcapi.get_driver_count():
            rcapi.register_all()

    @classmethod
    def driver_count(cls):
        """
        Returns the number of GDAL/OGR data source drivers registered.
        """
        return vcapi.get_driver_count() + rcapi.get_driver_count()

    @property
    def name(self):
        """
        Returns description/name string for this driver.
        """
        return force_text(rcapi.get_driver_description(self.ptr))
