"""
This module holds simple classes to convert geospatial values from the
database.
"""
from __future__ import unicode_literals

from decimal import Decimal

from django.contrib.gis.db.models.fields import GeoSelectFormatMixin
from django.contrib.gis.geometry.backend import Geometry
from django.contrib.gis.measure import Area, Distance


class BaseField(object):
    empty_strings_allowed = True

    def get_db_converters(self, connection):
        return [self.from_db_value]

    def select_format(self, compiler, sql, params):
        return sql, params


class AreaField(BaseField):
    "Wrapper for Area values."
    def __init__(self, area_att=None):
        self.area_att = area_att

    def from_db_value(self, value, expression, connection, context):
        if connection.features.interprets_empty_strings_as_nulls and value == '':
            value = None
        # If the database returns a Decimal, convert it to a float as expected
        # by the Python geometric objects.
        if isinstance(value, Decimal):
            value = float(value)
        # If the units are known, convert value into area measure.
        if value is not None and self.area_att:
            value = Area(**{self.area_att: value})
        return value

    def get_internal_type(self):
        return 'AreaField'


class DistanceField(BaseField):
    "Wrapper for Distance values."
    def __init__(self, distance_att):
        self.distance_att = distance_att

    def from_db_value(self, value, expression, connection, context):
        if value is not None:
            value = Distance(**{self.distance_att: value})
        return value

    def get_internal_type(self):
        return 'DistanceField'


class GeomField(GeoSelectFormatMixin, BaseField):
    """
    Wrapper for Geometry values.  It is a lightweight alternative to
    using GeometryField (which requires an SQL query upon instantiation).
    """
    # Hacky marker for get_db_converters()
    geom_type = None

    def from_db_value(self, value, expression, connection, context):
        if value is not None:
            value = Geometry(value)
        return value

    def get_internal_type(self):
        return 'GeometryField'


class GMLField(BaseField):
    """
    Wrapper for GML to be used by Oracle to ensure Database.LOB conversion.
    """

    def get_internal_type(self):
        return 'GMLField'

    def from_db_value(self, value, expression, connection, context):
        return value
