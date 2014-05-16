from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

# While this couples the geographic forms to the GEOS library,
# it decouples from database (by not importing SpatialBackend).
from django.contrib.gis.geos import GEOSException, GEOSGeometry
from .widgets import OpenLayersWidget


class GeometryField(forms.Field):
    """
    This is the basic form field for a Geometry.  Any textual input that is
    accepted by GEOSGeometry is accepted by this form.  By default,
    this includes WKT, HEXEWKB, WKB (in a buffer), and GeoJSON.
    """
    widget = OpenLayersWidget
    geom_type = 'GEOMETRY'

    default_error_messages = {
        'required': _('No geometry value provided.'),
        'invalid_geom': _('Invalid geometry value.'),
        'invalid_geom_type': _('Invalid geometry type.'),
        'transform_error': _('An error occurred when transforming the geometry '
                             'to the SRID of the geometry form field.'),
    }

    def __init__(self, **kwargs):
        # Pop out attributes from the database field, or use sensible
        # defaults (e.g., allow None).
        self.srid = kwargs.pop('srid', None)
        self.geom_type = kwargs.pop('geom_type', self.geom_type)
        super(GeometryField, self).__init__(**kwargs)
        self.widget.attrs['geom_type'] = self.geom_type

    def to_python(self, value):
        """
        Transforms the value to a Geometry object.
        """
        if value in self.empty_values:
            return None

        if not isinstance(value, GEOSGeometry):
            try:
                value = GEOSGeometry(value)
            except (GEOSException, ValueError, TypeError):
                raise forms.ValidationError(self.error_messages['invalid_geom'], code='invalid_geom')

        # Try to set the srid
        if not value.srid:
            try:
                value.srid = self.widget.map_srid
            except AttributeError:
                if self.srid:
                    value.srid = self.srid
        return value

    def clean(self, value):
        """
        Validates that the input value can be converted to a Geometry
        object (which is returned).  A ValidationError is raised if
        the value cannot be instantiated as a Geometry.
        """
        geom = super(GeometryField, self).clean(value)
        if geom is None:
            return geom

        # Ensuring that the geometry is of the correct type (indicated
        # using the OGC string label).
        if str(geom.geom_type).upper() != self.geom_type and not self.geom_type == 'GEOMETRY':
            raise forms.ValidationError(self.error_messages['invalid_geom_type'], code='invalid_geom_type')

        # Transforming the geometry if the SRID was set.
        if self.srid and self.srid != -1 and self.srid != geom.srid:
            try:
                geom.transform(self.srid)
            except GEOSException:
                raise forms.ValidationError(
                    self.error_messages['transform_error'], code='transform_error')

        return geom

    def _has_changed(self, initial, data):
        """ Compare geographic value of data with its initial value. """

        try:
            data = self.to_python(data)
            initial = self.to_python(initial)
        except forms.ValidationError:
            return True

        # Only do a geographic comparison if both values are available
        if initial and data:
            data.transform(initial.srid)
            # If the initial value was not added by the browser, the geometry
            # provided may be slightly different, the first time it is saved.
            # The comparison is done with a very low tolerance.
            return not initial.equals_exact(data, tolerance=0.000001)
        else:
            # Check for change of state of existence
            return bool(initial) != bool(data)


class GeometryCollectionField(GeometryField):
    geom_type = 'GEOMETRYCOLLECTION'


class PointField(GeometryField):
    geom_type = 'POINT'


class MultiPointField(GeometryField):
    geom_type = 'MULTIPOINT'


class LineStringField(GeometryField):
    geom_type = 'LINESTRING'


class MultiLineStringField(GeometryField):
    geom_type = 'MULTILINESTRING'


class PolygonField(GeometryField):
    geom_type = 'POLYGON'


class MultiPolygonField(GeometryField):
    geom_type = 'MULTIPOLYGON'
