__all__ = ['create_test_spatial_db', 'get_geo_where_clause', 'SpatialBackend']

from django.contrib.gis.db.backend.base import BaseSpatialBackend
from django.contrib.gis.db.backend.postgis.adaptor import PostGISAdaptor
from django.contrib.gis.db.backend.postgis.creation import create_test_spatial_db
from django.contrib.gis.db.backend.postgis.field import PostGISField
from django.contrib.gis.db.backend.postgis.models import GeometryColumns, SpatialRefSys
from django.contrib.gis.db.backend.postgis.query import *

SpatialBackend = BaseSpatialBackend(name='postgis', postgis=True,
                                    area=AREA,
                                    centroid=CENTROID,
                                    collect=COLLECT,
                                    difference=DIFFERENCE,
                                    distance=DISTANCE,
                                    distance_functions=DISTANCE_FUNCTIONS,
                                    distance_sphere=DISTANCE_SPHERE,
                                    distance_spheroid=DISTANCE_SPHEROID,
                                    envelope=ENVELOPE,
                                    extent=EXTENT,
                                    gis_terms=POSTGIS_TERMS,
                                    gml=ASGML,
                                    intersection=INTERSECTION,
                                    kml=ASKML,
                                    length=LENGTH,
                                    length_spheroid=LENGTH_SPHEROID,
                                    make_line=MAKE_LINE,
                                    mem_size=MEM_SIZE,
                                    num_geom=NUM_GEOM,
                                    num_points=NUM_POINTS,
                                    perimeter=PERIMETER,
                                    point_on_surface=POINT_ON_SURFACE,
                                    scale=SCALE,
                                    select=GEOM_SELECT,
                                    svg=ASSVG,
                                    sym_difference=SYM_DIFFERENCE,
                                    transform=TRANSFORM,
                                    translate=TRANSLATE,
                                    union=UNION,
                                    unionagg=UNIONAGG,
                                    version=(MAJOR_VERSION, MINOR_VERSION1, MINOR_VERSION2),
                                    Adaptor=PostGISAdaptor,
                                    Field=PostGISField,
                                    GeometryColumns=GeometryColumns,
                                    SpatialRefSys=SpatialRefSys,
                                    )
