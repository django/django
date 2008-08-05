"""
 The GeometryColumns and SpatialRefSys models for the Oracle spatial
 backend.

 It should be noted that Oracle Spatial does not have database tables
 named according to the OGC standard, so the closest analogs are used.
 For example, the `USER_SDO_GEOM_METADATA` is used for the GeometryColumns
 model and the `SDO_COORD_REF_SYS` is used for the SpatialRefSys model.
"""
from django.db import models
from django.contrib.gis.models import SpatialRefSysMixin

class GeometryColumns(models.Model):
    "Maps to the Oracle USER_SDO_GEOM_METADATA table."
    table_name = models.CharField(max_length=32)
    column_name = models.CharField(max_length=1024)
    srid = models.IntegerField(primary_key=True)
    # TODO: Add support for `diminfo` column (type MDSYS.SDO_DIM_ARRAY).
    class Meta:
        db_table = 'USER_SDO_GEOM_METADATA'

    @classmethod
    def table_name_col(cls):
        return 'table_name'

    def __unicode__(self):
        return '%s - %s (SRID: %s)' % (self.table_name, self.column_name, self.srid)

class SpatialRefSys(models.Model, SpatialRefSysMixin):
    "Maps to the Oracle MDSYS.CS_SRS table."
    cs_name = models.CharField(max_length=68)
    srid = models.IntegerField(primary_key=True)
    auth_srid = models.IntegerField()
    auth_name = models.CharField(max_length=256)
    wktext = models.CharField(max_length=2046)
    #cs_bounds = models.GeometryField()

    class Meta:
        # TODO: Figure out way to have this be MDSYS.CS_SRS without
        #  having django's quoting mess up the SQL.
        db_table = 'CS_SRS'

    @property
    def wkt(self):
        return self.wktext

    @classmethod
    def wkt_col(cls):
        return 'wktext'
