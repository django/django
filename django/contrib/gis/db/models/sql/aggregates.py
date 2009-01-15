from django.db.models.sql.aggregates import *

from django.contrib.gis.db.models.fields import GeometryField
from django.contrib.gis.db.backend import SpatialBackend

if SpatialBackend.oracle:
    geo_template = '%(function)s(SDOAGGRTYPE(%(field)s,%(tolerance)s))'
else:
    geo_template = '%(function)s(%(field)s)'

class GeoAggregate(Aggregate):
    # Overriding the SQL template with the geographic one.
    sql_template = geo_template

    is_extent = False

    def __init__(self, col, source=None, is_summary=False, **extra):
        super(GeoAggregate, self).__init__(col, source, is_summary, **extra)

        # Can't use geographic aggregates on non-geometry fields.
        if not isinstance(self.source, GeometryField):
            raise ValueError('Geospatial aggregates only allowed on geometry fields.')

        # Making sure the SQL function is available for this spatial backend.
        if not self.sql_function:
            raise NotImplementedError('This aggregate functionality not implemented for your spatial backend.')

class Extent(GeoAggregate):
    is_extent = True
    sql_function = SpatialBackend.extent

class MakeLine(GeoAggregate):
    sql_function = SpatialBackend.make_line

class Union(GeoAggregate):
    sql_function = SpatialBackend.unionagg
