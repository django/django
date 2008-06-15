__all__ = ['create_spatial_db', 'get_geo_where_clause', 'SpatialBackend']

from django.contrib.gis.db.backend.base import BaseSpatialBackend
from django.contrib.gis.db.backend.adaptor import WKTAdaptor
from django.contrib.gis.db.backend.mysql.creation import create_spatial_db
from django.contrib.gis.db.backend.mysql.field import MySQLGeoField
from django.contrib.gis.db.backend.mysql.query import *

SpatialBackend = BaseSpatialBackend(name='mysql', mysql=True,
                                    gis_terms=MYSQL_GIS_TERMS,
                                    select=GEOM_SELECT,
                                    Adaptor=WKTAdaptor,
                                    Field=MySQLGeoField)
