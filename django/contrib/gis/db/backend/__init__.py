"""
 This module provides the backend for spatial SQL construction with Django.

 Specifically, this module will import the correct routines and modules
 needed for GeoDjango to interface with the spatial database.
"""
from django.conf import settings
from django.contrib.gis.db.backend.util import gqn

# Retrieving the necessary settings from the backend.
if settings.DATABASE_ENGINE == 'postgresql_psycopg2':
    from django.contrib.gis.db.backend.postgis import create_test_spatial_db, get_geo_where_clause, SpatialBackend
elif settings.DATABASE_ENGINE == 'oracle':
    from django.contrib.gis.db.backend.oracle import create_test_spatial_db, get_geo_where_clause, SpatialBackend
elif settings.DATABASE_ENGINE == 'mysql':
    from django.contrib.gis.db.backend.mysql import create_test_spatial_db, get_geo_where_clause, SpatialBackend
elif settings.DATABASE_ENGINE == 'sqlite3':
    from django.contrib.gis.db.backend.spatialite import create_test_spatial_db, get_geo_where_clause, SpatialBackend
else:
    raise NotImplementedError('No Geographic Backend exists for %s' % settings.DATABASE_ENGINE)
