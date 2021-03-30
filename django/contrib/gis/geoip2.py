"""
This module houses the GeoIP2 object, a wrapper for the MaxMind GeoIP2(R)
Python API (https://geoip2.readthedocs.io/). This is an alternative to the
Python GeoIP2 interface provided by MaxMind.

GeoIP(R) is a registered trademark of MaxMind, Inc.

For IP-based geolocation, this module requires the GeoLite2 Country and City
datasets, in binary format (CSV will not work!). The datasets may be
downloaded from MaxMind at https://dev.maxmind.com/geoip/geoip2/geolite2/.
Grab GeoLite2-Country.mmdb.gz and GeoLite2-City.mmdb.gz, and unzip them in the
directory corresponding to settings.GEOIP_PATH.
"""

import socket
import warnings

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv46_address
from django.utils._os import to_path
from django.utils.deprecation import RemovedInDjango60Warning

__all__ = ["HAS_GEOIP2"]

try:
    import geoip2.database
except ImportError:  # pragma: no cover
    HAS_GEOIP2 = False
else:
    HAS_GEOIP2 = True
    __all__ += ["GeoIP2", "GeoIP2Exception"]


class GeoIP2Exception(Exception):
    pass


class GeoIP2:
    # The flags for GeoIP memory caching.
    # Try MODE_MMAP_EXT, MODE_MMAP, MODE_FILE in that order.
    MODE_AUTO = 0
    # Use the C extension with memory map.
    MODE_MMAP_EXT = 1
    # Read from memory map. Pure Python.
    MODE_MMAP = 2
    # Read database as standard file. Pure Python.
    MODE_FILE = 4
    # Load database into memory. Pure Python.
    MODE_MEMORY = 8
    cache_options = frozenset(
        (MODE_AUTO, MODE_MMAP_EXT, MODE_MMAP, MODE_FILE, MODE_MEMORY)
    )

    # Paths to the city & country binary databases.
    _city_file = ""
    _country_file = ""

    # Initially, pointers to GeoIP file references are NULL.
    _city = None
    _country = None

    def __init__(self, path=None, cache=0, country=None, city=None):
        """
        Initialize the GeoIP object. No parameters are required to use default
        settings. Keyword arguments may be passed in to customize the locations
        of the GeoIP datasets.

        * path: Base directory to where GeoIP data is located or the full path
            to where the city or country data files (*.mmdb) are located.
            Assumes that both the city and country data sets are located in
            this directory; overrides the GEOIP_PATH setting.

        * cache: The cache settings when opening up the GeoIP datasets. May be
            an integer in (0, 1, 2, 4, 8) corresponding to the MODE_AUTO,
            MODE_MMAP_EXT, MODE_MMAP, MODE_FILE, and MODE_MEMORY,
            `GeoIPOptions` C API settings,  respectively. Defaults to 0,
            meaning MODE_AUTO.

        * country: The name of the GeoIP country data file. Defaults to
            'GeoLite2-Country.mmdb'; overrides the GEOIP_COUNTRY setting.

        * city: The name of the GeoIP city data file. Defaults to
            'GeoLite2-City.mmdb'; overrides the GEOIP_CITY setting.
        """
        # Checking the given cache option.
        if cache not in self.cache_options:
            raise GeoIP2Exception("Invalid GeoIP caching option: %s" % cache)

        # Getting the GeoIP data path.
        path = path or getattr(settings, "GEOIP_PATH", None)
        if not path:
            raise GeoIP2Exception(
                "GeoIP path must be provided via parameter or the GEOIP_PATH setting."
            )

        path = to_path(path)
        if path.is_dir():
            # Constructing the GeoIP database filenames using the settings
            # dictionary. If the database files for the GeoLite country
            # and/or city datasets exist, then try to open them.
            country_db = path / (
                country or getattr(settings, "GEOIP_COUNTRY", "GeoLite2-Country.mmdb")
            )
            if country_db.is_file():
                self._country = geoip2.database.Reader(str(country_db), mode=cache)
                self._country_file = country_db

            city_db = path / (
                city or getattr(settings, "GEOIP_CITY", "GeoLite2-City.mmdb")
            )
            if city_db.is_file():
                self._city = geoip2.database.Reader(str(city_db), mode=cache)
                self._city_file = city_db
            if not self._reader:
                raise GeoIP2Exception("Could not load a database from %s." % path)
        elif path.is_file():
            # Otherwise, some detective work will be needed to figure out
            # whether the given database path is for the GeoIP country or city
            # databases.
            reader = geoip2.database.Reader(str(path), mode=cache)
            db_type = reader.metadata().database_type

            if "City" in db_type:
                # GeoLite City database detected.
                self._city = reader
                self._city_file = path
            elif "Country" in db_type:
                # GeoIP Country database detected.
                self._country = reader
                self._country_file = path
            else:
                raise GeoIP2Exception(
                    "Unable to recognize database edition: %s" % db_type
                )
        else:
            raise GeoIP2Exception("GeoIP path must be a valid file or directory.")

    @property
    def _reader(self):
        return self._country or self._city

    @property
    def _country_or_city(self):
        if self._country:
            return self._country.country
        else:
            return self._city.city

    def __del__(self):
        # Cleanup any GeoIP file handles lying around.
        if self._city:
            self._city.close()
        if self._country:
            self._country.close()

    def __repr__(self):
        meta = self._reader.metadata()
        version = "[v%s.%s]" % (
            meta.binary_format_major_version,
            meta.binary_format_minor_version,
        )
        return (
            '<%(cls)s %(version)s _country_file="%(country)s", _city_file="%(city)s">'
            % {
                "cls": self.__class__.__name__,
                "version": version,
                "country": self._country_file,
                "city": self._city_file,
            }
        )

    def _check_query(self, query, city=False, city_or_country=False):
        "Check the query and database availability."
        # Making sure a string was passed in for the query.
        if not isinstance(query, str):
            raise TypeError(
                "GeoIP query must be a string, not type %s" % type(query).__name__
            )

        # Extra checks for the existence of country and city databases.
        if city_or_country and not (self._country or self._city):
            raise GeoIP2Exception("Invalid GeoIP country and city data files.")
        elif city and not self._city:
            raise GeoIP2Exception("Invalid GeoIP city data file: %s" % self._city_file)

        # Return the query string back to the caller. GeoIP2 only takes IP addresses.
        try:
            validate_ipv46_address(query)
        except ValidationError:
            query = socket.gethostbyname(query)

        return query

    def city(self, query):
        """
        Return a dictionary of city information for the given IP address or
        Fully Qualified Domain Name (FQDN). Some information in the dictionary
        may be undefined (None).
        """
        enc_query = self._check_query(query, city=True)
        response = self._city.city(enc_query)
        region = response.subdivisions[0] if response.subdivisions else None
        return {
            "city": response.city.name,
            "continent_code": response.continent.code,
            "continent_name": response.continent.name,
            "country_code": response.country.iso_code,
            "country_name": response.country.name,
            "dma_code": response.location.metro_code,
            "is_in_european_union": response.country.is_in_european_union,
            "latitude": response.location.latitude,
            "longitude": response.location.longitude,
            "postal_code": response.postal.code,
            "region": region.iso_code if region else None,
            "time_zone": response.location.time_zone,
        }

    def country_code(self, query):
        "Return the country code for the given IP Address or FQDN."
        return self.country(query)["country_code"]

    def country_name(self, query):
        "Return the country name for the given IP Address or FQDN."
        return self.country(query)["country_name"]

    def country(self, query):
        """
        Return a dictionary with the country code and name when given an
        IP address or a Fully Qualified Domain Name (FQDN). For example, both
        '24.124.1.80' and 'djangoproject.com' are valid parameters.
        """
        # Returning the country code and name
        enc_query = self._check_query(query, city_or_country=True)
        response = self._country_or_city(enc_query)
        return {
            "country_code": response.country.iso_code,
            "country_name": response.country.name,
        }

    def coords(self, query, ordering=("longitude", "latitude")):
        warnings.warn(
            "GeoIP2.coords() is deprecated. Use GeoIP2.lon_lat() instead.",
            RemovedInDjango60Warning,
            stacklevel=2,
        )
        data = self.city(query)
        return tuple(data[o] for o in ordering)

    def lon_lat(self, query):
        "Return a tuple of the (longitude, latitude) for the given query."
        data = self.city(query)
        return data["longitude"], data["latitude"]

    def lat_lon(self, query):
        "Return a tuple of the (latitude, longitude) for the given query."
        data = self.city(query)
        return data["latitude"], data["longitude"]

    def geos(self, query):
        "Return a GEOS Point object for the given query."
        # Allows importing and using GeoIP2() when GEOS is not installed.
        from django.contrib.gis.geos import Point

        return Point(self.lon_lat(query), srid=4326)

    @classmethod
    def open(cls, full_path, cache):
        warnings.warn(
            "GeoIP2.open() is deprecated. Use GeoIP2() instead.",
            RemovedInDjango60Warning,
            stacklevel=2,
        )
        return GeoIP2(full_path, cache)
