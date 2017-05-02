import sys

from django.apps import AppConfig
from django.core import serializers
from django.utils.translation import gettext_lazy as _

from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.db import connections
from django.contrib.gis.db.backends.spatialite.base import DatabaseWrapper as SpatialiteDatabaseWrapper


class GISConfig(AppConfig):
    name = 'django.contrib.gis'
    verbose_name = _("GIS")

    def ready(self):
        if 'geojson' not in serializers.BUILTIN_SERIALIZERS:
            serializers.BUILTIN_SERIALIZERS['geojson'] = "django.contrib.gis.serializers.geojson"

        # Workaround for SpatiaLite: If a SpatiaLite database file doesn't
        # exist during migration, it will be created automatically. But in
        # that case, it doesn't have spatial metadata tables, so needs to be
        # initialized before migration.
        for conn in connections.all():
            if type(conn) == SpatialiteDatabaseWrapper:
                try:
                    cur = conn.cursor()
                    r = cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='spatial_ref_sys';")
                    if r.next()[0] == 0:
                        cur.execute("SELECT InitSpatialMetaData();")
                except Exception as msg:
                    new_msg = (
                        'An exception occurs during initializing spatial metadata: '
                        '%s') % (msg)
                    six.reraise(ImproperlyConfigured, ImproperlyConfigured(new_msg), sys.exc_info()[2])