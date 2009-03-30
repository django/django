from django.db.models.sql.aggregates import *
from django.contrib.gis.db.models.fields import GeometryField
from django.contrib.gis.db.models.sql.conversion import GeomField
from django.contrib.gis.db.backend import SpatialBackend

# Default SQL template for spatial aggregates.
geo_template = '%(function)s(%(field)s)'

# Default conversion functions for aggregates; will be overridden if implemented
# for the spatial backend.
def convert_extent(box):
    raise NotImplementedError('Aggregate extent not implemented for this spatial backend.')

def convert_geom(wkt, geo_field):
    raise NotImplementedError('Aggregate method not implemented for this spatial backend.')

if SpatialBackend.postgis:
    def convert_extent(box):
        # Box text will be something like "BOX(-90.0 30.0, -85.0 40.0)"; 
        # parsing out and returning as a 4-tuple.
        ll, ur = box[4:-1].split(',')
        xmin, ymin = map(float, ll.split())
        xmax, ymax = map(float, ur.split())
        return (xmin, ymin, xmax, ymax)

    def convert_geom(hex, geo_field):
        if hex: return SpatialBackend.Geometry(hex)
        else: return None
elif SpatialBackend.oracle:
    # Oracle spatial aggregates need a tolerance.
    geo_template = '%(function)s(SDOAGGRTYPE(%(field)s,%(tolerance)s))'

    def convert_extent(clob):
        if clob:
            # Oracle returns a polygon for the extent, we construct
            # the 4-tuple from the coordinates in the polygon.
            poly = SpatialBackend.Geometry(clob.read())
            shell = poly.shell
            ll, ur = shell[0], shell[2]
            xmin, ymin = ll
            xmax, ymax = ur
            return (xmin, ymin, xmax, ymax)
        else:
            return None
    
    def convert_geom(clob, geo_field):
        if clob: 
            return SpatialBackend.Geometry(clob.read(), geo_field.srid)
        else:
            return None
elif SpatialBackend.spatialite:
    # SpatiaLite returns WKT.
    def convert_geom(wkt, geo_field):
        if wkt:
            return SpatialBackend.Geometry(wkt, geo_field.srid)
        else:
            return None

class GeoAggregate(Aggregate):
    # Overriding the SQL template with the geographic one.
    sql_template = geo_template

    # Conversion class, if necessary.
    conversion_class = None

    # Flags for indicating the type of the aggregate.
    is_extent = False

    def __init__(self, col, source=None, is_summary=False, **extra):
        super(GeoAggregate, self).__init__(col, source, is_summary, **extra)

        if not self.is_extent and SpatialBackend.oracle:
            self.extra.setdefault('tolerance', 0.05)

        # Can't use geographic aggregates on non-geometry fields.
        if not isinstance(self.source, GeometryField): 
            raise ValueError('Geospatial aggregates only allowed on geometry fields.')

        # Making sure the SQL function is available for this spatial backend.
        if not self.sql_function:
            raise NotImplementedError('This aggregate functionality not implemented for your spatial backend.')

class Collect(GeoAggregate):
    conversion_class = GeomField
    sql_function = SpatialBackend.collect

class Extent(GeoAggregate):
    is_extent = True
    sql_function = SpatialBackend.extent
        
if SpatialBackend.oracle:
    # Have to change Extent's attributes here for Oracle.
    Extent.conversion_class = GeomField
    Extent.sql_template = '%(function)s(%(field)s)'

class MakeLine(GeoAggregate):
    conversion_class = GeomField
    sql_function = SpatialBackend.make_line

class Union(GeoAggregate):
    conversion_class = GeomField
    sql_function = SpatialBackend.unionagg
