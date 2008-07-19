from django import forms
from django.contrib.gis.geos import GEOSGeometry, GEOSException
from django.utils.translation import ugettext_lazy as _

class GeometryField(forms.Field):
    # By default a Textarea widget is used.
    widget = forms.Textarea

    default_error_messages = {
        'no_geom' : _(u'No geometry value provided.'),
        'invalid_geom' : _(u'Invalid Geometry value.'),
        'invalid_geom_type' : _(u'Invalid Geometry type.'),
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
            geom = GEOSGeometry(value)
            if geom.geom_type.upper() != self.geom_type:
                raise forms.ValidationError(self.error_messages['invalid_geom_type'])
            return geom
        except GEOSException:
            raise forms.ValidationError(self.error_messages['invalid_geom'])
