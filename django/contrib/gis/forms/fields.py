from django import forms
from django.utils.translation import ugettext_lazy as _

# While this couples the geographic forms to the GEOS library,
# it decouples from database (by not importing SpatialBackend).
from django.contrib.gis.geos import GEOSGeometry

class GeometryField(forms.Field):
    """
    This is the basic form field for a Geometry.  Any textual input that is
    accepted by GEOSGeometry is accepted by this form.  By default,
    this includes WKT, HEXEWKB, WKB (in a buffer), and GeoJSON.
    """
    widget = forms.Textarea

    default_error_messages = {
        'no_geom' : _(u'No geometry value provided.'),
        'invalid_geom' : _(u'Invalid geometry value.'),
        'invalid_geom_type' : _(u'Invalid geometry type.'),
        'transform_error' : _(u'An error occurred when transforming the geometry'
                              'to the SRID of the geometry form field.'),
        }

    def __init__(self, **kwargs):
        # Pop out attributes from the database field, or use sensible
        # defaults (e.g., allow None).
        self.srid = kwargs.pop('srid', None)
        self.geom_type = kwargs.pop('geom_type', 'GEOMETRY')
        self.null = kwargs.pop('null', True)
        super(GeometryField, self).__init__(**kwargs)

    def clean(self, value):
        """
        Validates that the input value can be converted to a Geometry
        object (which is returned).  A ValidationError is raised if
        the value cannot be instantiated as a Geometry.
        """
        if not value:
            if self.null and not self.required:
                # The geometry column allows NULL and is not required.
                return None
            else:
                raise forms.ValidationError(self.error_messages['no_geom'])

        # Trying to create a Geometry object from the form value.
        try:
            geom = GEOSGeometry(value)
        except:
            raise forms.ValidationError(self.error_messages['invalid_geom'])

        # Ensuring that the geometry is of the correct type (indicated
        # using the OGC string label).
        if str(geom.geom_type).upper() != self.geom_type and not self.geom_type == 'GEOMETRY':
            raise forms.ValidationError(self.error_messages['invalid_geom_type'])

        # Transforming the geometry if the SRID was set.
        if self.srid:
            if not geom.srid:
                # Should match that of the field if not given.
                geom.srid = self.srid
            elif self.srid != -1 and self.srid != geom.srid:
                try:
                    geom.transform(self.srid)
                except:
                    raise forms.ValidationError(self.error_messages['transform_error'])

        return geom
