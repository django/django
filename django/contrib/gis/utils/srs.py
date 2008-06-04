def add_postgis_srs(srs):
    """
    This function takes a GDAL SpatialReference system and adds its
    information to the PostGIS `spatial_ref_sys` table -- enabling
    spatial transformations with PostGIS.  This is handy for adding
    spatial reference systems not included by default with PostGIS.  
    For example, the following adds the so-called "Google Maps Mercator 
    Projection" (available in GDAL 1.5):
    
    >>> add_postgis_srs(SpatialReference(900913))

    Note: By default, the `auth_name` is set to 'EPSG' -- this should
    probably be changed.
    """
    from django.contrib.gis.models import SpatialRefSys
    from django.contrib.gis.gdal import SpatialReference

    if not isinstance(srs, SpatialReference):
        srs = SpatialReference(srs)

    if srs.srid is None:
        raise Exception('Spatial reference requires an SRID to be compatible with PostGIS.')
   
    # Creating the spatial_ref_sys model.
    sr, created = SpatialRefSys.objects.get_or_create(
        srid=srs.srid, auth_name='EPSG', auth_srid=srs.srid, 
        srtext=srs.wkt, proj4text=srs.proj4)
