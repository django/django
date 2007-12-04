"""
 The Oracle spatial database backend module.

 Please note that WKT support is broken on the XE version, and thus
 this backend will not work on such platforms.  Specifically, XE lacks 
 support for an internal JVM, and Java libraries are required to use 
 the WKT constructors.
"""
from django.contrib.gis.db.backend.oracle.creation import create_spatial_db
from django.contrib.gis.db.backend.oracle.field import OracleSpatialField, gqn
from django.contrib.gis.db.backend.oracle.query import \
     get_geo_where_clause, ORACLE_SPATIAL_TERMS, \
     ASGML, DISTANCE, GEOM_SELECT, TRANSFORM, UNION

