from __future__ import unicode_literals

from django.contrib.gis.gdal import HAS_GDAL
from django.core.serializers.base import (
    SerializationError, SerializerDoesNotExist,
)
from django.core.serializers.json import Serializer as JSONSerializer

if HAS_GDAL:
    from django.contrib.gis.gdal import CoordTransform, SpatialReference


class Serializer(JSONSerializer):
    """
    Convert a queryset to GeoJSON, http://geojson.org/
    """
    def _init_options(self):
        super(Serializer, self)._init_options()
        self.geometry_field = self.json_kwargs.pop('geometry_field', None)
        self.srs = SpatialReference(self.json_kwargs.pop('srid', 4326))

    def start_serialization(self):
        if not HAS_GDAL:
            # GDAL is needed for the geometry.geojson call
            raise SerializationError("The geojson serializer requires the GDAL library.")
        self._init_options()
        self._cts = {}  # cache of CoordTransform's
        self.stream.write(
            '{"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "EPSG:%d"}},'
            ' "features": [' % self.srs.srid)

    def end_serialization(self):
        self.stream.write(']}')

    def start_object(self, obj):
        super(Serializer, self).start_object(obj)
        self._geometry = None
        if self.geometry_field is None:
            # Find the first declared geometry field
            for field in obj._meta.fields:
                if hasattr(field, 'geom_type'):
                    self.geometry_field = field.name
                    break

    def get_dump_object(self, obj):
        data = {
            "type": "Feature",
            "properties": self._current,
        }
        if self._geometry:
            if self._geometry.srid != self.srs.srid:
                # If needed, transform the geometry in the srid of the global geojson srid
                if self._geometry.srid not in self._cts:
                    self._cts[self._geometry.srid] = CoordTransform(self._geometry.srs, self.srs)
                self._geometry.transform(self._cts[self._geometry.srid])
            data["geometry"] = eval(self._geometry.geojson)
        else:
            data["geometry"] = None
        return data

    def handle_field(self, obj, field):
        if field.name == self.geometry_field:
            self._geometry = field._get_val_from_obj(obj)
        else:
            super(Serializer, self).handle_field(obj, field)


class Deserializer(object):
    def __init__(self, *args, **kwargs):
        raise SerializerDoesNotExist("geojson is a serialization-only serializer")
