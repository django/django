"""
 The PostGIS spatial database backend module.
"""
from django.contrib.gis.db.backend.postgis.query import \
    get_geo_where_clause, geo_quotename, \
    GEOM_FUNC_PREFIX, POSTGIS_TERMS, \
    MAJOR_VERSION, MINOR_VERSION1, MINOR_VERSION2
from django.contrib.gis.db.backend.postgis.creation import create_spatial_db
from django.contrib.gis.db.backend.postgis.field import PostGISField

# Functions used by GeoManager methods, and not via lookup types.
if MAJOR_VERSION == 1:
    if MINOR_VERSION1 == 3:
        ASKML = 'ST_AsKML'
        ASGML = 'ST_AsGML'
        UNION = 'ST_Union'
    elif MINOR_VERSION1 == 2 and MINOR_VERSION2 >= 1:
        ASKML = 'AsKML'
        ASGML = 'AsGML'
        UNION = 'GeomUnion'
        

    
