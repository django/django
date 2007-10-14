"""
 The PostGIS spatial database backend module.
"""
from django.contrib.gis.db.backend.postgis.creation import create_spatial_db
from django.contrib.gis.db.backend.postgis.field import PostGISField, gqn
from django.contrib.gis.db.backend.postgis.query import \
    get_geo_where_clause, GEOM_FUNC_PREFIX, POSTGIS_TERMS, \
    MAJOR_VERSION, MINOR_VERSION1, MINOR_VERSION2, \
    ASKML, ASGML, GEOM_FROM_TEXT, UNION, TRANSFORM, GEOM_SELECT
