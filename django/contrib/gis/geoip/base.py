import os
import re
import warnings
from ctypes import c_char_p

from django.contrib.gis.geoip.libgeoip import GEOIP_SETTINGS
from django.contrib.gis.geoip.prototypes import (
    GeoIP_country_code_by_addr, GeoIP_country_code_by_name,
    GeoIP_country_name_by_addr, GeoIP_country_name_by_name,
    GeoIP_database_info, GeoIP_delete, GeoIP_lib_version, GeoIP_open,
    GeoIP_record_by_addr, GeoIP_record_by_name,
)
from django.core.validators import ipv4_re
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.encoding import force_bytes, force_text

# Regular expressions for recognizing the GeoIP free database editions.
free_regex = re.compile(r'^GEO-\d{3}FREE')
lite_regex = re.compile(r'^GEO-\d{3}LITE')


class GeoIPException(Exception):
    pass


class GeoIP(object):
    # The flags for GeoIP memory caching.
    # GEOIP_STANDARD - read database from filesystem, uses least memory.
    #
    # GEOIP_MEMORY_CACHE - load database into memory, faster performance
    #        but uses more memory
    #
    # GEOIP_CHECK_CACHE - check for updated database.  If database has been
    #        updated, reload filehandle and/or memory cache.  This option
    #        is not thread safe.
    #
    # GEOIP_INDEX_CACHE - just cache the most frequently accessed index
    #        portion of the database, resulting in faster lookups than
    #        GEOIP_STANDARD, but less memory usage than GEOIP_MEMORY_CACHE -
    #        useful for larger databases such as GeoIP Organization and
    #        GeoIP City.  Note, for GeoIP Country, Region and Netspeed
    #        databases, GEOIP_INDEX_CACHE is equivalent to GEOIP_MEMORY_CACHE
    #
    # GEOIP_MMAP_CACHE - load database into mmap shared memory ( not available
    #       on Windows).
    GEOIP_STANDARD = 0
    GEOIP_MEMORY_CACHE = 1
    GEOIP_CHECK_CACHE = 2
    GEOIP_INDEX_CACHE = 4
    GEOIP_MMAP_CACHE = 8
    cache_options = {opt: None for opt in (0, 1, 2, 4, 8)}

    # Paths to the city & country binary databases.
    _city_file = ''
    _country_file = ''

    # Initially, pointers to GeoIP file references are NULL.
    _city = None
    _country = None

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
            and may be an integer in (0, 1, 2, 4, 8) corresponding to
            the GEOIP_STANDARD, GEOIP_MEMORY_CACHE, GEOIP_CHECK_CACHE,
            GEOIP_INDEX_CACHE, and GEOIP_MMAP_CACHE, `GeoIPOptions` C API
            settings,  respectively.  Defaults to 0, meaning that the data is read
            from the disk.

        * country: The name of the GeoIP country data file.  Defaults to
            'GeoIP.dat'; overrides the GEOIP_COUNTRY settings attribute.

        * city: The name of the GeoIP city data file.  Defaults to
            'GeoLiteCity.dat'; overrides the GEOIP_CITY settings attribute.
        """

        warnings.warn(
            "django.contrib.gis.geoip is deprecated in favor of "
            "django.contrib.gis.geoip2 and the MaxMind GeoLite2 database "
            "format.", RemovedInDjango20Warning, 2
        )

        # Checking the given cache option.
        if cache in self.cache_options:
            self._cache = cache
        else:
            raise GeoIPException('Invalid GeoIP caching option: %s' % cache)

        # Getting the GeoIP data path.
        if not path:
            path = GEOIP_SETTINGS.get('GEOIP_PATH')
            if not path:
                raise GeoIPException('GeoIP path must be provided via parameter or the GEOIP_PATH setting.')
        if not isinstance(path, six.string_types):
            raise TypeError('Invalid path type: %s' % type(path).__name__)

        if os.path.isdir(path):
            # Constructing the GeoIP database filenames using the settings
            # dictionary.  If the database files for the GeoLite country
            # and/or city datasets exist, then try and open them.
            country_db = os.path.join(path, country or GEOIP_SETTINGS.get('GEOIP_COUNTRY', 'GeoIP.dat'))
            if os.path.isfile(country_db):
                self._country = GeoIP_open(force_bytes(country_db), cache)
                self._country_file = country_db

            city_db = os.path.join(path, city or GEOIP_SETTINGS.get('GEOIP_CITY', 'GeoLiteCity.dat'))
            if os.path.isfile(city_db):
                self._city = GeoIP_open(force_bytes(city_db), cache)
                self._city_file = city_db
        elif os.path.isfile(path):
            # Otherwise, some detective work will be needed to figure
            # out whether the given database path is for the GeoIP country
            # or city databases.
            ptr = GeoIP_open(force_bytes(path), cache)
            info = GeoIP_database_info(ptr)
            if lite_regex.match(info):
                # GeoLite City database detected.
                self._city = ptr
                self._city_file = path
            elif free_regex.match(info):
                # GeoIP Country database detected.
                self._country = ptr
                self._country_file = path
            else:
                raise GeoIPException('Unable to recognize database edition: %s' % info)
        else:
            raise GeoIPException('GeoIP path must be a valid file or directory.')

    def __del__(self):
        # Cleaning any GeoIP file handles lying around.
        if GeoIP_delete is None:
            return
        if self._country:
            GeoIP_delete(self._country)
        if self._city:
            GeoIP_delete(self._city)

    def __repr__(self):
        version = ''
        if GeoIP_lib_version is not None:
            version += ' [v%s]' % force_text(GeoIP_lib_version())
        return '<%(cls)s%(version)s _country_file="%(country)s", _city_file="%(city)s">' % {
            'cls': self.__class__.__name__,
            'version': version,
            'country': self._country_file,
            'city': self._city_file,
        }

    def _check_query(self, query, country=False, city=False, city_or_country=False):
        "Helper routine for checking the query and database availability."
        # Making sure a string was passed in for the query.
        if not isinstance(query, six.string_types):
            raise TypeError('GeoIP query must be a string, not type %s' % type(query).__name__)

        # Extra checks for the existence of country and city databases.
        if city_or_country and not (self._country or self._city):
            raise GeoIPException('Invalid GeoIP country and city data files.')
        elif country and not self._country:
            raise GeoIPException('Invalid GeoIP country data file: %s' % self._country_file)
        elif city and not self._city:
            raise GeoIPException('Invalid GeoIP city data file: %s' % self._city_file)

        # Return the query string back to the caller. GeoIP only takes bytestrings.
        return force_bytes(query)

    def city(self, query):
        """
        Returns a dictionary of city information for the given IP address or
        Fully Qualified Domain Name (FQDN).  Some information in the dictionary
        may be undefined (None).
        """
        enc_query = self._check_query(query, city=True)
        if ipv4_re.match(query):
            # If an IP address was passed in
            return GeoIP_record_by_addr(self._city, c_char_p(enc_query))
        else:
            # If a FQDN was passed in.
            return GeoIP_record_by_name(self._city, c_char_p(enc_query))

    def country_code(self, query):
        "Returns the country code for the given IP Address or FQDN."
        enc_query = self._check_query(query, city_or_country=True)
        if self._country:
            if ipv4_re.match(query):
                return GeoIP_country_code_by_addr(self._country, enc_query)
            else:
                return GeoIP_country_code_by_name(self._country, enc_query)
        else:
            return self.city(query)['country_code']

    def country_name(self, query):
        "Returns the country name for the given IP Address or FQDN."
        enc_query = self._check_query(query, city_or_country=True)
        if self._country:
            if ipv4_re.match(query):
                return GeoIP_country_name_by_addr(self._country, enc_query)
            else:
                return GeoIP_country_name_by_name(self._country, enc_query)
        else:
            return self.city(query)['country_name']

    def country(self, query):
        """
        Returns a dictionary with the country code and name when given an
        IP address or a Fully Qualified Domain Name (FQDN).  For example, both
        '24.124.1.80' and 'djangoproject.com' are valid parameters.
        """
        # Returning the country code and name
        return {'country_code': self.country_code(query),
                'country_name': self.country_name(query),
                }

    # #### Coordinate retrieval routines ####
    def coords(self, query, ordering=('longitude', 'latitude')):
        cdict = self.city(query)
        if cdict is None:
            return None
        else:
            return tuple(cdict[o] for o in ordering)

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

    # #### GeoIP Database Information Routines ####
    @property
    def country_info(self):
        "Returns information about the GeoIP country database."
        if self._country is None:
            ci = 'No GeoIP Country data in "%s"' % self._country_file
        else:
            ci = GeoIP_database_info(self._country)
        return ci

    @property
    def city_info(self):
        "Returns information about the GeoIP city database."
        if self._city is None:
            ci = 'No GeoIP City data in "%s"' % self._city_file
        else:
            ci = GeoIP_database_info(self._city)
        return ci

    @property
    def info(self):
        "Returns information about the GeoIP library and databases in use."
        info = ''
        if GeoIP_lib_version:
            info += 'GeoIP Library:\n\t%s\n' % GeoIP_lib_version()
        return info + 'Country:\n\t%s\nCity:\n\t%s' % (self.country_info, self.city_info)

    # #### Methods for compatibility w/the GeoIP-Python API. ####
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
