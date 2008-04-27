"""
 This module provides the backend for spatial SQL construction with Django.

 Specifically, this module will import the correct routines and modules
 needed for GeoDjango.
 
 (1) `GeoBackEndField`, a base class needed for GeometryField.
 (2) `GeoWhereNode`, a subclass of `WhereNode` used to contruct spatial SQL.
 (3) `SpatialBackend`, a container object for information specific to the
     spatial backend.
"""
from django.conf import settings
from django.db.models.sql.query import QUERY_TERMS
from django.db.models.sql.where import WhereNode
from django.contrib.gis.db.backend.util import gqn

# These routines (needed by GeoManager), default to False.
ASGML, ASKML, DISTANCE, DISTANCE_SPHEROID, EXTENT, TRANSFORM, UNION, VERSION = tuple(False for i in range(8))

# Lookup types in which the rest of the parameters are not
# needed to be substitute in the WHERE SQL (e.g., the 'relate'
# operation on Oracle does not need the mask substituted back
# into the query SQL.).
LIMITED_WHERE = []

# Retrieving the necessary settings from the backend.
if settings.DATABASE_ENGINE == 'postgresql_psycopg2':
    from django.contrib.gis.db.backend.postgis.adaptor import \
        PostGISAdaptor as GeoAdaptor
    from django.contrib.gis.db.backend.postgis.field import \
        PostGISField as GeoBackendField
    from django.contrib.gis.db.backend.postgis.creation import create_spatial_db
    from django.contrib.gis.db.backend.postgis.query import \
        get_geo_where_clause, POSTGIS_TERMS as GIS_TERMS, \
        ASGML, ASKML, DISTANCE, DISTANCE_SPHEROID, DISTANCE_FUNCTIONS, \
        EXTENT, GEOM_SELECT, TRANSFORM, UNION, \
        MAJOR_VERSION, MINOR_VERSION1, MINOR_VERSION2
    # PostGIS version info is needed to determine calling order of some
    # stored procedures (e.g., AsGML()).
    VERSION = (MAJOR_VERSION, MINOR_VERSION1, MINOR_VERSION2)
    SPATIAL_BACKEND = 'postgis'
elif settings.DATABASE_ENGINE == 'oracle':
    from django.contrib.gis.db.backend.adaptor import WKTAdaptor as GeoAdaptor
    from django.contrib.gis.db.backend.oracle.field import \
        OracleSpatialField as GeoBackendField
    from django.contrib.gis.db.backend.oracle.creation import create_spatial_db
    from django.contrib.gis.db.backend.oracle.query import \
        get_geo_where_clause, ORACLE_SPATIAL_TERMS as GIS_TERMS, \
        ASGML, DISTANCE, DISTANCE_FUNCTIONS, GEOM_SELECT, TRANSFORM, UNION
    SPATIAL_BACKEND = 'oracle'
    LIMITED_WHERE = ['relate']
elif settings.DATABASE_ENGINE == 'mysql':
    from django.contrib.gis.db.backend.adaptor import WKTAdaptor as GeoAdaptor
    from django.contrib.gis.db.backend.mysql.field import \
        MySQLGeoField as GeoBackendField
    from django.contrib.gis.db.backend.mysql.creation import create_spatial_db
    from django.contrib.gis.db.backend.mysql.query import \
        get_geo_where_clause, MYSQL_GIS_TERMS as GIS_TERMS, GEOM_SELECT
    DISTANCE_FUNCTIONS = {}
    SPATIAL_BACKEND = 'mysql'
else:
    raise NotImplementedError('No Geographic Backend exists for %s' % settings.DATABASE_ENGINE)

class GeoWhereNode(WhereNode):
    """
    The GeoWhereNode calls the `get_geo_where_clause` from the appropriate
    spatial backend in order to construct correct spatial SQL.
    """
    def make_atom(self, child, qn):
        table_alias, name, field, lookup_type, value = child
        if hasattr(field, '_geom'):
            if lookup_type in GIS_TERMS:
                # Getting the geographic where clause; substitution parameters
                # will be populated in the GeoFieldSQL object returned by the
                # GeometryField.
                gwc = get_geo_where_clause(lookup_type, table_alias, field, value)
                where, params = field.get_db_prep_lookup(lookup_type, value)
                return gwc % tuple(where), params
            else:
                raise TypeError('Invalid lookup type: %r' % lookup_type)
        else:
            # If not a GeometryField, call the `make_atom` from the 
            # base class.
            return super(GeoWhereNode, self).make_atom(child, qn)

class SpatialBackend(object):
    "A container for properties of the SpatialBackend."
    # Stored procedure names used by the `GeoManager`.
    as_kml = ASKML
    as_gml = ASGML
    distance = DISTANCE
    distance_spheroid = DISTANCE_SPHEROID
    extent = EXTENT
    name = SPATIAL_BACKEND
    select = GEOM_SELECT
    transform = TRANSFORM
    union = UNION
    
    # Version information, if defined.
    version = VERSION
    
    # All valid GIS lookup terms, and distance functions.
    gis_terms = GIS_TERMS
    distance_functions = DISTANCE_FUNCTIONS
    
    # Lookup types where additional WHERE parameters are excluded.
    limited_where = LIMITED_WHERE

    # Class for the backend field.
    Field = GeoBackendField

    # Adaptor class used for quoting GEOS geometries in the database.
    Adaptor = GeoAdaptor
