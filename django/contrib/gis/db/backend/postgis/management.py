"""
  This utility module is for obtaining information about the PostGIS
   installation.

  See PostGIS docs at Ch. 6.2.1 for more information on these functions.
"""
import re

def _get_postgis_func(func):
    "Helper routine for calling PostGIS functions and returning their result."
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute('SELECT %s()' % func)
    row = cursor.fetchone()
    cursor.close()
    return row[0]

### PostGIS management functions ###
def postgis_geos_version():
    "Returns the version of the GEOS library used with PostGIS."
    return _get_postgis_func('postgis_geos_version')

def postgis_lib_version():
    "Returns the version number of the PostGIS library used with PostgreSQL."
    return _get_postgis_func('postgis_lib_version')

def postgis_proj_version():
    "Returns the version of the PROJ.4 library used with PostGIS."
    return _get_postgis_func('postgis_proj_version')

def postgis_version():
    "Returns PostGIS version number and compile-time options."
    return _get_postgis_func('postgis_version')

def postgis_full_version():
    "Returns PostGIS version number and compile-time options."
    return _get_postgis_func('postgis_full_version')

### Routines for parsing output of management functions. ###
version_regex = re.compile('^(?P<major>\d)\.(?P<minor1>\d)\.(?P<minor2>\d+)')
def postgis_version_tuple():
    "Returns the PostGIS version as a tuple."

    # Getting the PostGIS version
    version = postgis_lib_version()
    m = version_regex.match(version)
    if m:
        major = int(m.group('major'))
        minor1 = int(m.group('minor1'))
        minor2 = int(m.group('minor2'))
    else:
        raise Exception('Could not parse PostGIS version string: %s' % version)

    return (version, major, minor1, minor2)
