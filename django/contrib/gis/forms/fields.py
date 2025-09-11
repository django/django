from django import forms
from django.contrib.gis.gdal import GDALException
from django.contrib.gis.geos import GEOSException, GEOSGeometry
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .widgets import OpenLayersWidget


class GeometryField(forms.Field):
    """
    This is the basic form field for a Geometry. Any textual input that is
    accepted by GEOSGeometry is accepted by this form. By default,
    this includes WKT, HEXEWKB, WKB (in a buffer), and GeoJSON.
    """

    widget = OpenLayersWidget
    geom_type = "GEOMETRY"

    default_error_messages = {
        "required": _("No geometry value provided."),
        "invalid_geom": _("Invalid geometry value."),
        "invalid_geom_type": _("Invalid geometry type."),
        "transform_error": _(
            "An error occurred when transforming the geometry "
            "to the SRID of the geometry form field."
        ),
    }

    def __init__(self, *, srid=None, geom_type=None, **kwargs):
        self.srid = srid
        if geom_type is not None:
            self.geom_type = geom_type
        super().__init__(**kwargs)
        self.widget.attrs["geom_type"] = self.geom_type

    def to_python(self, value):
        """Transform the value to a Geometry object."""
        if value in self.empty_values:
            return None

        if not isinstance(value, GEOSGeometry):
            if hasattr(self.widget, "deserialize"):
                try:
                    value = self.widget.deserialize(value)
                except GDALException:
                    value = None
            else:
                try:
                    value = GEOSGeometry(value)
                except (GEOSException, ValueError, TypeError):
                    value = None
            if value is None:
                raise ValidationError(
                    self.error_messages["invalid_geom"], code="invalid_geom"
                )

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
        Validate that the input value can be converted to a Geometry object
        and return it. Raise a ValidationError if the value cannot be
        instantiated as a Geometry.
        """
        geom = super().clean(value)
        if geom is None:
            return geom

        # Ensuring that the geometry is of the correct type (indicated
        # using the OGC string label).
        if (
            str(geom.geom_type).upper() != self.geom_type
            and self.geom_type != "GEOMETRY"
        ):
            raise ValidationError(
                self.error_messages["invalid_geom_type"], code="invalid_geom_type"
            )

        # Transforming the geometry if the SRID was set.
        if self.srid and self.srid != -1 and self.srid != geom.srid:
            try:
                geom.transform(self.srid)
            except GEOSException:
                raise ValidationError(
                    self.error_messages["transform_error"], code="transform_error"
                )

        return geom

    def has_changed(self, initial, data):
        """Compare geographic value of data with its initial value."""

        try:
            data = self.to_python(data)
            initial = self.to_python(initial)
        except ValidationError:
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
    geom_type = "GEOMETRYCOLLECTION"


class PointField(GeometryField):
    geom_type = "POINT"


class MultiPointField(GeometryField):
    geom_type = "MULTIPOINT"


class LineStringField(GeometryField):
    geom_type = "LINESTRING"


class MultiLineStringField(GeometryField):
    geom_type = "MULTILINESTRING"


class PolygonField(GeometryField):
    geom_type = "POLYGON"


class MultiPolygonField(GeometryField):
    geom_type = "MULTIPOLYGON"
