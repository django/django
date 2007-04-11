import re
from django.db import models

"""
  Models for the PostGIS/OGC database tables.
"""

# For pulling out the spheroid from the spatial reference string.
#  TODO: Flattening not used in all ellipsoids, could also be a minor axis, or 'b'
#        parameter.
spheroid_regex = re.compile(r'.+SPHEROID\[\"(?P<name>.+)\",(?P<major>\d+(\.\d+)?),(?P<flattening>\d{3}\.\d+),')

# For pulling out the projected coordinate system units.  Python regexs are greedy
#  by default, so this should get the units of the projection instead (PROJCS)
#  of the units for the geographic coordinate system (GEOGCS).
unit_regex = re.compile(r'^PROJCS.+UNIT\[\"(?P<units>[a-z]+)\", ?(?P<conversion>[0-9\.]+), ?(AUTHORITY\[\"(?P<authority>[a-z0-9 \.]+)\",[ ]?\"(?P<code>\d+)\"\])?', re.I)

# This is the global 'geometry_columns' from PostGIS.
#   See PostGIS Documentation at Ch. 4.2.2
class GeometryColumns(models.Model):
    f_table_catalog = models.CharField(maxlength=256)
    f_table_schema = models.CharField(maxlength=256)
    f_table_name = models.CharField(maxlength=256)
    f_geometry_column = models.CharField(maxlength=256)
    coord_dimension = models.IntegerField()
    srid = models.IntegerField()
    type = models.CharField(maxlength=30)

    class Meta:
        db_table = 'geometry_columns'

# This is the global 'spatial_ref_sys' table from PostGIS.
#   See PostGIS Documentation at Ch. 4.2.1
class SpatialRefSys(models.Model):
    srid = models.IntegerField(primary_key=True)
    auth_name = models.CharField(maxlength=256)
    auth_srid = models.IntegerField()
    srtext = models.CharField(maxlength=2048)
    proj4text = models.CharField(maxlength=2048)

    class Meta:
        db_table = 'spatial_ref_sys'
                                                                                
    @property
    def spheroid(self):
        "Pulls out the spheroid from the srtext."
        m = spheroid_regex.match(self.srtext)
        if m:
            return (m.group('name'), float(m.group('major')), float(m.group('flattening')))
        else:
            return None

    @property
    def projected_units(self):
        "If the spatial reference system is projected, get the units or return None."
        m = unit_regex.match(self.srtext)
        if m:
            if m.group('authority'):
                authority = (m.group('authority'), int(m.group('code')))
            else:
                authority = None
            return (m.group('units'), float(m.group('conversion')), authority)
        else:
            return None

    def __str__(self):
        return "%d - %s " % (self.srid, self.auth_name)
