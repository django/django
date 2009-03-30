"""
This module holds simple classes used by GeoQuery.convert_values
to convert geospatial values from the database.
"""
from django.contrib.gis.db.backend import SpatialBackend

class BaseField(object):
    def get_internal_type(self):
        "Overloaded method so OracleQuery.convert_values doesn't balk."
        return None

if SpatialBackend.oracle: BaseField.empty_strings_allowed = False

class AreaField(BaseField):
    "Wrapper for Area values."
    def __init__(self, area_att):
        self.area_att = area_att

class DistanceField(BaseField):
    "Wrapper for Distance values."
    def __init__(self, distance_att):
        self.distance_att = distance_att

class GeomField(BaseField):
    """
    Wrapper for Geometry values.  It is a lightweight alternative to 
    using GeometryField (which requires a SQL query upon instantiation).
    """
    pass
