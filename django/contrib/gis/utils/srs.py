def add_postgis_srs(srs, auth_name='EPSG', auth_srid=None, ref_sys_name=None):
    """
    This function takes a GDAL SpatialReference system and adds its
    information to the PostGIS `spatial_ref_sys` table -- enabling
    spatial transformations with PostGIS.  This is handy for adding
    spatial reference systems not included by default with PostGIS.
    For example, the following adds the so-called "Google Maps Mercator
    Projection" (available in GDAL 1.5):

    >>> add_postgis_srs(SpatialReference(900913))

    Keyword Arguments:
     auth_name: This keyword may be customized with the value of the
                `auth_name` field.  Defaults to 'EPSG'.

     auth_srid: This keyword may be customized with the value of the
                `auth_srid` field.  Defaults to the SRID determined
                by GDAL.

     ref_sys_name: For SpatiaLite users only, sets the value of the
                   the `ref_sys_name` field.  Defaults to the name
                   determined by GDAL.
    """
    from django.contrib.gis.db.backend import SpatialBackend
    from django.contrib.gis.models import SpatialRefSys
    from django.contrib.gis.gdal import SpatialReference

    if SpatialBackend.oracle or SpatialBackend.mysql:
        raise Exception('This utility not supported on Oracle or MySQL spatial backends.')

    if not isinstance(srs, SpatialReference):
        srs = SpatialReference(srs)

    if srs.srid is None:
        raise Exception('Spatial reference requires an SRID to be compatible with PostGIS.')

    # Initializing the keyword arguments dictionary for both PostGIS and SpatiaLite.
    kwargs = {'srid' : srs.srid,
              'auth_name' : auth_name,
              'auth_srid' : auth_srid or srs.srid,
              'proj4text' : srs.proj4,
              }

    # Backend-specific keyword settings.
    if SpatialBackend.postgis: kwargs['srtext'] = srs.wkt
    if SpatialBackend.spatialite: kwargs['ref_sys_name'] = ref_sys_name or srs.name

    # Creating the spatial_ref_sys model.
    sr, created = SpatialRefSys.objects.get_or_create(**kwargs)
