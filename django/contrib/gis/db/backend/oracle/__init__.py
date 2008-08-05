__all__ = ['create_spatial_db', 'get_geo_where_clause', 'SpatialBackend']

from django.contrib.gis.db.backend.base import BaseSpatialBackend
from django.contrib.gis.db.backend.oracle.adaptor import OracleSpatialAdaptor
from django.contrib.gis.db.backend.oracle.creation import create_spatial_db
from django.contrib.gis.db.backend.oracle.field import OracleSpatialField
from django.contrib.gis.db.backend.oracle.query import *

SpatialBackend = BaseSpatialBackend(name='oracle', oracle=True,
                                    area=AREA,
                                    centroid=CENTROID,
                                    difference=DIFFERENCE,
                                    distance=DISTANCE,
                                    distance_functions=DISTANCE_FUNCTIONS,
                                    gis_terms=ORACLE_SPATIAL_TERMS,
                                    gml=ASGML,
                                    intersection=INTERSECTION,
                                    length=LENGTH,
                                    limited_where = {'relate' : None},
                                    num_geom=NUM_GEOM,
                                    num_points=NUM_POINTS,
                                    perimeter=LENGTH,
                                    point_on_surface=POINT_ON_SURFACE,
                                    select=GEOM_SELECT,
                                    sym_difference=SYM_DIFFERENCE,
                                    transform=TRANSFORM,
                                    unionagg=UNIONAGG,
                                    union=UNION,
                                    Adaptor=OracleSpatialAdaptor,
                                    Field=OracleSpatialField,
                                    )
