"""
 This module houses the GeoIP object, a ctypes wrapper for the MaxMind GeoIP(R)
  C API (http://www.maxmind.com/app/c).

 GeoIP(R) is a registered trademark of MaxMind, LLC of Boston, Massachusetts.

 For IP-based geolocation, this module requires the GeoLite Country and City
  datasets, in binary format (CSV will not work!).  The datasets may be 
  downloaded from MaxMind at http://www.maxmind.com/download/geoip/database/.
  Grab GeoIP.dat.gz and GeoLiteCity.dat.gz, and unzip them in the directory
  corresponding to settings.GEOIP_PATH.  See the GeoIP docstring and examples
  below for more details.

 TODO: Verify compatibility with Windows.

 Example:

 >>> from django.contrib.gis.utils import GeoIP
 >>> g = GeoIP()
 >>> g.country('google.com')
 {'country_code': 'US', 'country_name': 'United States'}
 >>> g.city('72.14.207.99')
 {'area_code': 650,
 'city': 'Mountain View',
 'country_code': 'US',
 'country_code3': 'USA',
 'country_name': 'United States',
 'dma_code': 807,
 'latitude': 37.419200897216797,
 'longitude': -122.05740356445312,
 'postal_code': '94043',
 'region': 'CA'}
 >>> g.lat_lon('salon.com')
 (37.789798736572266, -122.39420318603516)
 >>> g.lon_lat('uh.edu')
 (-95.415199279785156, 29.77549934387207) 
 >>> g.geos('24.124.1.80').wkt
 'POINT (-95.2087020874023438 39.0392990112304688)'
"""
import os, re
from ctypes import c_char_p, c_float, c_int, string_at, Structure, CDLL, POINTER
from django.conf import settings

# The Exception class for GeoIP Errors.
class GeoIPException(Exception): pass

# The shared library for the GeoIP C API.  May be downloaded
#  from http://www.maxmind.com/download/geoip/api/c/
if os.name == 'nt':
    ext = '.dll'
elif os.name == 'posix':
    platform = os.uname()[0]
    if platform in ('Linux', 'SunOS'):
        ext = '.so'
    elif platofm == 'Darwin':
        ext = '.dylib'
    else:
        raise GeoIPException('Unknown POSIX platform "%s"' % platform)
lgeoip = CDLL('libGeoIP' + ext)

# A regular expression for recognizing IP addresses
ipregex = re.compile(r'^(?P<w>\d\d?\d?)\.(?P<x>\d\d?\d?)\.(?P<y>\d\d?\d?)\.(?P<z>\d\d?\d?)$')

# The flags for GeoIP memory caching.
# GEOIP_STANDARD - read database from filesystem, uses least memory.
#
# GEOIP_MEMORY_CACHE - load database into memory, faster performance
#        but uses more memory
#
# GEOIP_CHECK_CACHE - check for updated database.  If database has been updated,
#        reload filehandle and/or memory cache.
#
# GEOIP_INDEX_CACHE - just cache
#        the most frequently accessed index portion of the database, resulting
#        in faster lookups than GEOIP_STANDARD, but less memory usage than
#        GEOIP_MEMORY_CACHE - useful for larger databases such as
#        GeoIP Organization and GeoIP City.  Note, for GeoIP Country, Region
#        and Netspeed databases, GEOIP_INDEX_CACHE is equivalent to GEOIP_MEMORY_CACHE
#
cache_options = {0 : c_int(0), # GEOIP_STANDARD
                 1 : c_int(1), # GEOIP_MEMORY_CACHE
                 2 : c_int(2), # GEOIP_CHECK_CACHE
                 4 : c_int(4), # GEOIP_INDEX_CACHE
                 }

# GeoIPRecord C Structure definition.
class GeoIPRecord(Structure):
    _fields_ = [('country_code', c_char_p),
                ('country_code3', c_char_p),
                ('country_name', c_char_p),
                ('region', c_char_p),
                ('city', c_char_p),
                ('postal_code', c_char_p),
                ('latitude', c_float),
                ('longitude', c_float),
                ('dma_code', c_int),
                ('area_code', c_int),
                ]

# ctypes function prototypes
record_by_addr = lgeoip.GeoIP_record_by_addr
record_by_addr.restype = POINTER(GeoIPRecord)
record_by_name = lgeoip.GeoIP_record_by_name
record_by_name.restype = POINTER(GeoIPRecord)

# The exception class for GeoIP Errors.
class GeoIPException(Exception): pass

class GeoIP(object):
    def __init__(self, path=None, country=None, city=None,
                 cache=0):
        """
        Initializes the GeoIP object, no parameters are required to use default
         settings.  Keyword arguments may be passed in to customize the locations
         of the GeoIP data sets.

        * path: Base directory where the GeoIP data files (*.dat) are located.
            Assumes that both the city and country data sets are located in
            this directory.  Overrides the GEOIP_PATH settings attribute.

        * country: The name of the GeoIP country data file.  Defaults to
            'GeoIP.dat'; overrides the GEOIP_COUNTRY settings attribute.

        * city: The name of the GeoIP city data file.  Defaults to
            'GeoLiteCity.dat'; overrides the GEOIP_CITY settings attribute.

        * cache: The cache settings when opening up the GeoIP datasets,
            and may be an integer in (0, 1, 2, 4).  Defaults to 0, meaning
            that the data is read from the disk.
        """

        # Checking the given cache option.
        if cache in cache_options:
            self._cache = cache_options[cache]
        else:
            raise GeoIPException('Invalid caching option: %s' % cache)

        # Getting the GeoIP data path.
        if not path:
            try:
                self._path = settings.GEOIP_PATH
            except AttributeError:
                raise GeoIPException('Must specify GEOIP_PATH in your settings.py')
        else:
            self._path = path
        if not os.path.isdir(self._path):
            raise GeoIPException('GEOIP_PATH must be set to a directory.')

        # Getting the GeoIP country data file.
        if not country:
            try:
                cntry_file = settings.GEOIP_COUNTRY
            except AttributeError:
                cntry_file = 'GeoIP.dat'
        else:
            cntry_file = country
        self._country_file = os.path.join(self._path, cntry_file)

        # Getting the GeoIP city data file.
        if not city:
            try:
                city_file = settings.GEOIP_CITY
            except AttributeError:
                city_file = 'GeoLiteCity.dat'
        else:
            city_file = city
        self._city_file = os.path.join(self._path, city_file)

        # Opening up the GeoIP country data file.
        if os.path.isfile(self._country_file):
            self._country = lgeoip.GeoIP_open(c_char_p(self._country_file), self._cache)
        else:
            self._country = None

        # Opening the GeoIP city data file.
        if os.path.isfile(self._city_file):
            self._city = lgeoip.GeoIP_open(c_char_p(self._city_file), self._cache)
        else:
            self._city = None
    
    def country(self, query):
        """
        Returns a dictonary with with the country code and name when given an 
         IP address or a Fully Qualified Domain Name (FQDN).  For example, both
         '24.124.1.80' and 'djangoproject.com' are valid parameters.
        """
        if self._country is None:
            raise GeoIPException('Invalid GeoIP country data file: %s' % self._country_file)

        if ipregex.match(query):
            # If an IP address was passed in.
            code = lgeoip.GeoIP_country_code_by_addr(self._country, c_char_p(query))
            name = lgeoip.GeoIP_country_name_by_addr(self._country, c_char_p(query))
        else:
            # If a FQDN was passed in.
            code = lgeoip.GeoIP_country_code_by_name(self._country, c_char_p(query))
            name = lgeoip.GeoIP_country_name_by_name(self._country, c_char_p(query))

        # Checking our returned country code and name, setting each to
        #  None, if pointer is invalid.
        if bool(code): code = string_at(code)
        else: code = None
        if bool(name): name = string_at(name)
        else: name = None

        # Returning the country code and name
        return {'country_code' : code, 
                'country_name' : name,
                }

    def city(self, query):
        """
        Returns a dictionary of city information for the given IP address or 
         Fully Qualified Domain Name (FQDN).  Some information in the dictionary
         may be undefined (None).
        """
        if self._city is None:
            raise GeoIPException('Invalid GeoIP country data file: %s' % self._city_file)

        if ipregex.match(query):
            # If an IP address was passed in
            ptr = record_by_addr(self._city, c_char_p(query))
        else:
            # If a FQDN was passed in.
            ptr = record_by_name(self._city, c_char_p(query))

        # Checking the pointer to the C structure, if valid pull out elements
        #  into a dicionary and return.
        if bool(ptr):
            record = ptr.contents
            return dict((tup[0], getattr(record, tup[0])) for tup in record._fields_)
        else:
            return None

    #### Coordinate retrieval routines ####
    def _coords(self, query, ordering):
        cdict = self.city(query)
        if cdict is None: return None
        else: return tuple(cdict[o] for o in ordering)
    
    def lon_lat(self, query):
        "Returns a tuple of the (longitude, latitude) for the given query."
        return self._coords(query, ('longitude', 'latitude'))

    def lat_lon(self, query):
        "Returns a tuple of the (latitude, longitude) for the given query."
        return self._coords(query, ('latitude', 'longitude'))

    def geos(self, query):
        "Returns a GEOS Point object for the given query."
        ll = self.lon_lat(query)
        if ll:
            from django.contrib.gis.geos import Point
            return Point(ll, srid=4326)
        else:
            return None

    #### GeoIP Database Information Routines ####
    def country_info(self):
        "Returns information about the GeoIP country database."
        if self._country is None:
            ci = 'No GeoIP Country data in "%s"' % self._country_file
        else:
            ci = string_at(lgeoip.GeoIP_database_info(self._country))
        return ci
    country_info = property(country_info)

    def city_info(self):
        "Retuns information about the GeoIP city database."
        if self._city is None:
            ci = 'No GeoIP City data in "%s"' % self._city_file
        else:
            ci = string_at(lgeoip.GeoIP_database_info(self._city))
        return ci
    city_info = property(city_info)
        
    def info(self):
        "Returns information about all GeoIP databases in use."
        return 'Country:\n\t%s\nCity:\n\t%s' % (self.country_info, self.city_info)
    info = property(info)
