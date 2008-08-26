from django import forms
from django.contrib.gis.db.backend import SpatialBackend
from django.utils.translation import ugettext_lazy as _

class GeometryField(forms.Field):
    """
    This is the basic form field for a Geometry.  Any textual input that is
    accepted by SpatialBackend.Geometry is accepted by this form.  By default, 
    this is GEOSGeometry, which accepts WKT, HEXEWKB, WKB, and GeoJSON.
    """
    widget = forms.Textarea

    default_error_messages = {
        'no_geom' : _(u'No geometry value provided.'),
        'invalid_geom' : _(u'Invalid geometry value.'),
        'invalid_geom_type' : _(u'Invalid geometry type.'),
    }

    def __init__(self, **kwargs):
        self.null = kwargs.pop('null')
        self.geom_type = kwargs.pop('geom_type')
        super(GeometryField, self).__init__(**kwargs)

    def clean(self, value):
        """
        Validates that the input value can be converted to a Geometry
        object (which is returned).  A ValidationError is raised if
        the value cannot be instantiated as a Geometry.
        """
        if not value:
            if self.null:
                # The geometry column allows NULL, return None.
                return None
            else:
                raise forms.ValidationError(self.error_messages['no_geom'])
     
        try:
            # Trying to create a Geometry object from the form value.
            geom = SpatialBackend.Geometry(value)
        except:
            raise forms.ValidationError(self.error_messages['invalid_geom'])
  
        # Ensuring that the geometry is of the correct type (indicated
        # using the OGC string label).
        if str(geom.geom_type).upper() != self.geom_type and not self.geom_type == 'GEOMETRY':
            raise forms.ValidationError(self.error_messages['invalid_geom_type'])

        return geom
