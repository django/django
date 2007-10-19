"""
 The MySQL spatial database backend module.

 Please note that MySQL only supports bounding box queries, also
 known as MBRs (Minimum Bounding Rectangles).  Moreover, spatial
 indices may only be used on MyISAM tables -- if you need 
 transactions, take a look at PostGIS.
"""

from django.contrib.gis.db.backend.mysql.creation import create_spatial_db
from django.contrib.gis.db.backend.mysql.field import MySQLGeoField, gqn
from django.contrib.gis.db.backend.mysql.query import get_geo_where_clause, MYSQL_GIS_TERMS, GEOM_SELECT
