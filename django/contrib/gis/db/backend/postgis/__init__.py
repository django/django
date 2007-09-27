"""
 The PostGIS spatial database backend module.
"""
from django.contrib.gis.db.backend.postgis.query import \
    get_geo_where_clause, geo_quotename, \
    GEOM_FUNC_PREFIX, POSTGIS_TERMS, \
    MAJOR_VERSION, MINOR_VERSION1, MINOR_VERSION2
from django.contrib.gis.db.backend.postgis.creation import create_spatial_db
from django.contrib.gis.db.backend.postgis.field import PostGISField

# Whether PostGIS has AsKML() support.
if MAJOR_VERSION == 1:
    # AsKML() only supported in versions 1.2.1+
    if MINOR_VERSION1 == 3:
        ASKML = 'ST_AsKML'
    elif MINOR_VERSION1 == 2 and MINOR_VERSION2 >= 1:
        ASKML = 'AsKML'
    
