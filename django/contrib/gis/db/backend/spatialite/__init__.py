__all__ = ['create_test_spatial_db', 'get_geo_where_clause', 'SpatialBackend']

from ctypes.util import find_library
from django.conf import settings
from django.db.backends.signals import connection_created

from django.contrib.gis.db.backend.base import BaseSpatialBackend
from django.contrib.gis.db.backend.spatialite.adaptor import SpatiaLiteAdaptor
from django.contrib.gis.db.backend.spatialite.creation import create_test_spatial_db
from django.contrib.gis.db.backend.spatialite.field import SpatiaLiteField
from django.contrib.gis.db.backend.spatialite.models import GeometryColumns, SpatialRefSys
from django.contrib.gis.db.backend.spatialite.query import *

# Here we are figuring out the path to the SpatiLite library (`libspatialite`).
# If it's not in the system PATH, it may be set manually in the settings via
# the `SPATIALITE_LIBRARY_PATH` setting.
spatialite_lib = getattr(settings, 'SPATIALITE_LIBRARY_PATH', find_library('spatialite'))
if spatialite_lib:
    def initialize_spatialite(sender=None, **kwargs):
        """
        This function initializes the pysqlite2 connection to enable the
        loading of extensions, and to load up the SpatiaLite library
        extension.
        """
        from django.db import connection
        connection.connection.enable_load_extension(True)
        connection.cursor().execute("SELECT load_extension(%s)", (spatialite_lib,))
    connection_created.connect(initialize_spatialite)
else:
    # No SpatiaLite library found.
    raise Exception('Unable to locate SpatiaLite, needed to use GeoDjango with sqlite3.')

SpatialBackend = BaseSpatialBackend(name='spatialite', spatialite=True,
                                    area=AREA,
                                    centroid=CENTROID,
                                    contained=CONTAINED,
                                    difference=DIFFERENCE,
                                    distance=DISTANCE,
                                    distance_functions=DISTANCE_FUNCTIONS,
                                    envelope=ENVELOPE,
                                    from_text=GEOM_FROM_TEXT,
                                    gis_terms=SPATIALITE_TERMS,
                                    intersection=INTERSECTION,
                                    length=LENGTH,
                                    num_geom=NUM_GEOM,
                                    num_points=NUM_POINTS,
                                    point_on_surface=POINT_ON_SURFACE,
                                    scale=SCALE,
                                    select=GEOM_SELECT,
                                    sym_difference=SYM_DIFFERENCE,
                                    transform=TRANSFORM,
                                    translate=TRANSLATE,
                                    union=UNION,
                                    unionagg=UNIONAGG,
                                    Adaptor=SpatiaLiteAdaptor,
                                    Field=SpatiaLiteField,
                                    GeometryColumns=GeometryColumns,
                                    SpatialRefSys=SpatialRefSys,
                                    )
