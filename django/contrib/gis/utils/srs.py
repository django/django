from django.contrib.gis.gdal import SpatialReference
from django.db import DEFAULT_DB_ALIAS, connections


def add_srs_entry(srs, auth_name='EPSG', auth_srid=None, ref_sys_name=None,
                  database=None):
    """
    This function takes a GDAL SpatialReference system and adds its information
    to the `spatial_ref_sys` table of the spatial backend.  Doing this enables
    database-level spatial transformations for the backend.  Thus, this utility
    is useful for adding spatial reference systems not included by default with
    the backend:

    >>> from django.contrib.gis.utils import add_srs_entry
    >>> add_srs_entry(3857)

    Keyword Arguments:
     auth_name:
       This keyword may be customized with the value of the `auth_name` field.
       Defaults to 'EPSG'.

     auth_srid:
       This keyword may be customized with the value of the `auth_srid` field.
       Defaults to the SRID determined by GDAL.

     ref_sys_name:
       For SpatiaLite users only, sets the value of the `ref_sys_name` field.
       Defaults to the name determined by GDAL.

     database:
      The name of the database connection to use; the default is the value
      of `django.db.DEFAULT_DB_ALIAS` (at the time of this writing, its value
      is 'default').
    """
    if not database:
        database = DEFAULT_DB_ALIAS
    connection = connections[database]

    if not hasattr(connection.ops, 'spatial_version'):
        raise Exception('The `add_srs_entry` utility only works '
                        'with spatial backends.')
    if not connection.features.supports_add_srs_entry:
        raise Exception('This utility does not support your database backend.')
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
    kwargs = {'srid': srs.srid,
              'auth_name': auth_name,
              'auth_srid': auth_srid or srs.srid,
              'proj4text': srs.proj4,
              }

    # Backend-specific fields for the SpatialRefSys model.
    srs_field_names = {f.name for f in SpatialRefSys._meta.get_fields()}
    if 'srtext' in srs_field_names:
        kwargs['srtext'] = srs.wkt
    if 'ref_sys_name' in srs_field_names:
        # Spatialite specific
        kwargs['ref_sys_name'] = ref_sys_name or srs.name

    # Creating the spatial_ref_sys model.
    try:
        # Try getting via SRID only, because using all kwargs may
        # differ from exact wkt/proj in database.
        SpatialRefSys.objects.using(database).get(srid=srs.srid)
    except SpatialRefSys.DoesNotExist:
        SpatialRefSys.objects.using(database).create(**kwargs)

# Alias is for backwards-compatibility purposes.
add_postgis_srs = add_srs_entry
