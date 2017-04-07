"""
This module holds simple classes to convert geospatial values from the
database.
"""
from decimal import Decimal

from django.contrib.gis.measure import Area, Distance
from django.db import models


class AreaField(models.FloatField):
    "Wrapper for Area values."
    def __init__(self, area_att=None):
        self.area_att = area_att

    def get_prep_value(self, value):
        if not isinstance(value, Area):
            raise ValueError('AreaField only accepts Area measurement objects.')
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        if value is None or not self.area_att:
            return value
        return getattr(value, self.area_att)

    def from_db_value(self, value, expression, connection, context):
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


class DistanceField(models.FloatField):
    "Wrapper for Distance values."
    def __init__(self, distance_att=None):
        self.distance_att = distance_att

    def get_prep_value(self, value):
        if isinstance(value, Distance):
            return value
        return super().get_prep_value(value)

    def get_db_prep_value(self, value, connection, prepared=False):
        if not isinstance(value, Distance):
            return value
        if not self.distance_att:
            raise ValueError('Distance measure is supplied, but units are unknown for result.')
        return getattr(value, self.distance_att)

    def from_db_value(self, value, expression, connection, context):
        if value is None or not self.distance_att:
            return value
        return Distance(**{self.distance_att: value})

    def get_internal_type(self):
        return 'DistanceField'
