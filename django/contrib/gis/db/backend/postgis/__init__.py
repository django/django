"""
  The PostGIS spatial database backend module.
"""
from query import get_geo_where_clause, GEOM_FUNC_PREFIX, POSTGIS_TERMS
from creation import create_spatial_db
from field import PostGISField

