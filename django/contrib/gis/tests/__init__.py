def geo_apps():
    """
    Returns a list of GeoDjango test applications that reside in
    `django.contrib.gis.tests` that can be used with the current
    database and the spatial libraries that are installed.
    """
    from django.db import connection
    from django.contrib.gis.geos import GEOS_PREPARE
    from django.contrib.gis.gdal import HAS_GDAL

    apps = ['geoapp', 'relatedapp']

    # No distance queries on MySQL.
    if not connection.ops.mysql:
        apps.append('distapp')

    # Test geography support with PostGIS 1.5+.
    if connection.ops.postgis and connection.ops.geography:
        apps.append('geogapp')

    # The following GeoDjango test apps depend on GDAL support.
    if HAS_GDAL:
        # Geographic admin, LayerMapping, and ogrinspect test apps
        # all require GDAL.
        apps.extend(['geoadmin', 'layermap', 'inspectapp'])

        # 3D apps use LayerMapping, which uses GDAL and require GEOS 3.1+.
        if connection.ops.postgis and GEOS_PREPARE:
            apps.append('geo3d')
    return [('django.contrib.gis.tests', app) for app in apps]
