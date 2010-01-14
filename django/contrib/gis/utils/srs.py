from django.contrib.gis.gdal import SpatialReference
from django.db import connections, DEFAULT_DB_ALIAS

def add_srs_entry(srs, auth_name='EPSG', auth_srid=None, ref_sys_name=None,
                  database=DEFAULT_DB_ALIAS):
    """
    This function takes a GDAL SpatialReference system and adds its information
    to the `spatial_ref_sys` table of the spatial backend.  Doing this enables
    database-level spatial transformations for the backend.  Thus, this utility
    is useful for adding spatial reference systems not included by default with
    the backend -- for example, the so-called "Google Maps Mercator Projection"
    is excluded in PostGIS 1.3 and below, and the following adds it to the
    `spatial_ref_sys` table:

    >>> from django.contrib.gis.utils import add_srs_entry
    >>> add_srs_entry(900913)

    Keyword Arguments:
     auth_name:
       This keyword may be customized with the value of the `auth_name` field.
       Defaults to 'EPSG'.

     auth_srid:
       This keyword may be customized with the value of the `auth_srid` field.
       Defaults to the SRID determined by GDAL.

     ref_sys_name:
       For SpatiaLite users only, sets the value of the the `ref_sys_name` field.
       Defaults to the name determined by GDAL.

     database:
      The name of the database connection to use; the default is the value
      of `django.db.DEFAULT_DB_ALIAS` (at the time of this writing, it's value
      is 'default').
    """
    connection = connections[database]
    if not hasattr(connection.ops, 'spatial_version'):
        raise Exception('The `add_srs_entry` utility only works '
                        'with spatial backends.')
    if connection.ops.oracle or connection.ops.mysql:
        raise Exception('This utility does not support the '
                        'Oracle or MySQL spatial backends.')
    SpatialRefSys = connection.ops.spatial_ref_sys()

    # If argument is not a `SpatialReference` instance, use it as parameter
    # to construct a `SpatialReference` instance.
    if not isinstance(srs, SpatialReference):
        srs = SpatialReference(srs)

    if srs.srid is None:
        raise Exception('Spatial reference requires an SRID to be '
                        'compatible with the spatial backend.')

    # Initializing the keyword arguments dictionary for both PostGIS
    # and SpatiaLite.
    kwargs = {'srid' : srs.srid,
              'auth_name' : auth_name,
              'auth_srid' : auth_srid or srs.srid,
              'proj4text' : srs.proj4,
              }

    # Backend-specific fields for the SpatialRefSys model.
    if connection.ops.postgis:
        kwargs['srtext'] = srs.wkt
    if connection.ops.spatialite:
        kwargs['ref_sys_name'] = ref_sys_name or srs.name

    # Creating the spatial_ref_sys model.
    try:
        # Try getting via SRID only, because using all kwargs may
        # differ from exact wkt/proj in database.
        sr = SpatialRefSys.objects.get(srid=srs.srid)
    except SpatialRefSys.DoesNotExist:
        sr = SpatialRefSys.objects.create(**kwargs)

# Alias is for backwards-compatibility purposes.
add_postgis_srs = add_srs_entry
