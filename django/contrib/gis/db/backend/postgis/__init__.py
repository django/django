"""
  The PostGIS spatial database backend module.
"""
from query import \
    get_geo_where_clause, GEOM_FUNC_PREFIX, POSTGIS_TERMS, \
    MAJOR_VERSION, MINOR_VERSION1, MINOR_VERSION2
from creation import create_spatial_db
from field import PostGISField

# Whether PostGIS has AsKML() support.
if MAJOR_VERSION == 1:
    # AsKML() only supported in versions 1.2.1+
    if MINOR_VERSION1 == 3:
        ASKML = 'ST_AsKML'
    elif MINOR_VERSION1 == 2 and MINOR_VERSION2 >= 1:
        ASKML = 'AsKML'
    
