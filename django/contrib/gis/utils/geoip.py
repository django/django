"""
 This module houses the GeoIP object, a ctypes wrapper for the MaxMind GeoIP(R)
 C API (http://www.maxmind.com/app/c).  This is an alternative to the GPL
 licensed Python GeoIP interface provided by MaxMind.

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
from ctypes import c_char_p, c_float, c_int, Structure, CDLL, POINTER
from ctypes.util import find_library
from django.conf import settings
if not settings.configured: settings.configure()

# Creating the settings dictionary with any settings, if needed.
GEOIP_SETTINGS = dict((key, getattr(settings, key)) 
                      for key in ('GEOIP_PATH', 'GEOIP_LIBRARY_PATH', 'GEOIP_COUNTRY', 'GEOIP_CITY')
                      if hasattr(settings, key))
lib_path = GEOIP_SETTINGS.get('GEOIP_LIBRARY_PATH', None)

# GeoIP Exception class.
class GeoIPException(Exception): pass

# The shared library for the GeoIP C API.  May be downloaded
#  from http://www.maxmind.com/download/geoip/api/c/
if lib_path:
    lib_name = None
else:
    # TODO: Is this really the library name for Windows?
    lib_name = 'GeoIP'

# Getting the path to the GeoIP library.
if lib_name: lib_path = find_library(lib_name)
if lib_path is None: raise GeoIPException('Could not find the GeoIP library (tried "%s"). '
                                          'Try setting GEOIP_LIBRARY_PATH in your settings.' % lib_name)
lgeoip = CDLL(lib_path)

# Regular expressions for recognizing IP addresses and the GeoIP
# free database editions.
ipregex = re.compile(r'^(?P<w>\d\d?\d?)\.(?P<x>\d\d?\d?)\.(?P<y>\d\d?\d?)\.(?P<z>\d\d?\d?)$')
free_regex = re.compile(r'^GEO-\d{3}FREE')
lite_regex = re.compile(r'^GEO-\d{3}LITE')

#### GeoIP C Structure definitions ####
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
class GeoIPTag(Structure): pass

#### ctypes function prototypes ####
RECTYPE = POINTER(GeoIPRecord)
DBTYPE = POINTER(GeoIPTag)

# For retrieving records by name or address.
def record_output(func):
    func.restype = RECTYPE
    return func
rec_by_addr = record_output(lgeoip.GeoIP_record_by_addr)
rec_by_name = record_output(lgeoip.GeoIP_record_by_name)

# For opening up GeoIP databases.
geoip_open = lgeoip.GeoIP_open
geoip_open.restype = DBTYPE

# String output routines.
def string_output(func):
    func.restype = c_char_p
    return func
geoip_dbinfo = string_output(lgeoip.GeoIP_database_info)
cntry_code_by_addr = string_output(lgeoip.GeoIP_country_code_by_addr)
cntry_code_by_name = string_output(lgeoip.GeoIP_country_code_by_name)
cntry_name_by_addr = string_output(lgeoip.GeoIP_country_name_by_addr)
cntry_name_by_name = string_output(lgeoip.GeoIP_country_name_by_name)

#### GeoIP class ####
class GeoIP(object):
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
    GEOIP_STANDARD = 0
    GEOIP_MEMORY_CACHE = 1
    GEOIP_CHECK_CACHE = 2
    GEOIP_INDEX_CACHE = 4
    cache_options = dict((opt, None) for opt in (0, 1, 2, 4))

    def __init__(self, path=None, cache=0, country=None, city=None):
        """
        Initializes the GeoIP object, no parameters are required to use default
        settings.  Keyword arguments may be passed in to customize the locations
        of the GeoIP data sets.

        * path: Base directory to where GeoIP data is located or the full path
            to where the city or country data files (*.dat) are located.
            Assumes that both the city and country data sets are located in
            this directory; overrides the GEOIP_PATH settings attribute.

        * cache: The cache settings when opening up the GeoIP datasets,
            and may be an integer in (0, 1, 2, 4) corresponding to
            the GEOIP_STANDARD, GEOIP_MEMORY_CACHE, GEOIP_CHECK_CACHE,
            and GEOIP_INDEX_CACHE `GeoIPOptions` C API settings,
            respectively.  Defaults to 0, meaning that the data is read
            from the disk.

        * country: The name of the GeoIP country data file.  Defaults to
            'GeoIP.dat'; overrides the GEOIP_COUNTRY settings attribute.

        * city: The name of the GeoIP city data file.  Defaults to
            'GeoLiteCity.dat'; overrides the GEOIP_CITY settings attribute.
        """
        # Checking the given cache option.
        if cache in self.cache_options:
            self._cache = self.cache_options[cache]
        else:
            raise GeoIPException('Invalid caching option: %s' % cache)

        # Getting the GeoIP data path.
        if not path:
            path = GEOIP_SETTINGS.get('GEOIP_PATH', None)
            if not path: raise GeoIPException('GeoIP path must be provided via parameter or the GEOIP_PATH setting.')
        if not isinstance(path, basestring):
            raise TypeError('Invalid path type: %s' % type(path).__name__)

        cntry_ptr, city_ptr = (None, None)
        if os.path.isdir(path):
            # Getting the country and city files using the settings
            # dictionary.  If no settings are provided, default names
            # are assigned.
            country = os.path.join(path, country or GEOIP_SETTINGS.get('GEOIP_COUNTRY', 'GeoIP.dat'))
            city = os.path.join(path, city or GEOIP_SETTINGS.get('GEOIP_CITY', 'GeoLiteCity.dat'))
        elif os.path.isfile(path):
            # Otherwise, some detective work will be needed to figure
            # out whether the given database path is for the GeoIP country
            # or city databases.
            ptr = geoip_open(path, cache)
            info = geoip_dbinfo(ptr)
            if lite_regex.match(info):
                # GeoLite City database.
                city, city_ptr = path, ptr
            elif free_regex.match(info):
                # GeoIP Country database.
                country, cntry_ptr = path, ptr
            else:
                raise GeoIPException('Unable to recognize database edition: %s' % info)
        else:
            raise GeoIPException('GeoIP path must be a valid file or directory.')
        
        # `_init_db` does the dirty work.
        self._init_db(country, cache, '_country', cntry_ptr)
        self._init_db(city, cache, '_city', city_ptr)

    def _init_db(self, db_file, cache, attname, ptr=None):
        "Helper routine for setting GeoIP ctypes database properties."
        if ptr:
            # Pointer already retrieved.
            pass
        elif os.path.isfile(db_file or ''):
            ptr = geoip_open(db_file, cache)
        setattr(self, attname, ptr)
        setattr(self, '%s_file' % attname, db_file)

    def _check_query(self, query, country=False, city=False, city_or_country=False):
        "Helper routine for checking the query and database availability."
        # Making sure a string was passed in for the query.
        if not isinstance(query, basestring):
            raise TypeError('GeoIP query must be a string, not type %s' % type(query).__name__)

        # Extra checks for the existence of country and city databases.
        if city_or_country and self._country is None and self._city is None:
            raise GeoIPException('Invalid GeoIP country and city data files.')
        elif country and self._country is None:
            raise GeoIPException('Invalid GeoIP country data file: %s' % self._country_file)
        elif city and self._city is None:
            raise GeoIPException('Invalid GeoIP city data file: %s' % self._city_file)

    def city(self, query):
        """
        Returns a dictionary of city information for the given IP address or
        Fully Qualified Domain Name (FQDN).  Some information in the dictionary
        may be undefined (None).
        """
        self._check_query(query, city=True)
        if ipregex.match(query):
            # If an IP address was passed in
            ptr = rec_by_addr(self._city, c_char_p(query))
        else:
            # If a FQDN was passed in.
            ptr = rec_by_name(self._city, c_char_p(query))

        # Checking the pointer to the C structure, if valid pull out elements
        # into a dicionary and return.
        if bool(ptr):
            record = ptr.contents
            return dict((tup[0], getattr(record, tup[0])) for tup in record._fields_)
        else:
            return None
    
    def country_code(self, query):
        "Returns the country code for the given IP Address or FQDN."
        self._check_query(query, city_or_country=True)
        if self._country:
            if ipregex.match(query): return cntry_code_by_addr(self._country, query)
            else: return cntry_code_by_name(self._country, query)
        else:
            return self.city(query)['country_code']

    def country_name(self, query):
        "Returns the country name for the given IP Address or FQDN."
        self._check_query(query, city_or_country=True)
        if self._country:
            if ipregex.match(query): return cntry_name_by_addr(self._country, query)
            else: return cntry_name_by_name(self._country, query)
        else:
            return self.city(query)['country_name']

    def country(self, query):
        """
        Returns a dictonary with with the country code and name when given an 
        IP address or a Fully Qualified Domain Name (FQDN).  For example, both
        '24.124.1.80' and 'djangoproject.com' are valid parameters.
        """
        # Returning the country code and name
        return {'country_code' : self.country_code(query), 
                'country_name' : self.country_name(query),
                }

    #### Coordinate retrieval routines ####
    def coords(self, query, ordering=('longitude', 'latitude')):
        cdict = self.city(query)
        if cdict is None: return None
        else: return tuple(cdict[o] for o in ordering)

    def lon_lat(self, query):
        "Returns a tuple of the (longitude, latitude) for the given query."
        return self.coords(query)

    def lat_lon(self, query):
        "Returns a tuple of the (latitude, longitude) for the given query."
        return self.coords(query, ('latitude', 'longitude'))

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
            ci = geoip_dbinfo(self._country)
        return ci
    country_info = property(country_info)

    def city_info(self):
        "Retuns information about the GeoIP city database."
        if self._city is None:
            ci = 'No GeoIP City data in "%s"' % self._city_file
        else:
            ci = geoip_dbinfo(self._city)
        return ci
    city_info = property(city_info)
        
    def info(self):
        "Returns information about all GeoIP databases in use."
        return 'Country:\n\t%s\nCity:\n\t%s' % (self.country_info, self.city_info)
    info = property(info)

    #### Methods for compatibility w/the GeoIP-Python API. ####
    @classmethod
    def open(cls, full_path, cache):
        return GeoIP(full_path, cache)

    def _rec_by_arg(self, arg):
        if self._city:
            return self.city(arg)
        else:
            return self.country(arg)
    region_by_addr = city
    region_by_name = city
    record_by_addr = _rec_by_arg
    record_by_name = _rec_by_arg
    country_code_by_addr = country_code
    country_code_by_name = country_code
    country_name_by_addr = country_name
    country_name_by_name = country_name
