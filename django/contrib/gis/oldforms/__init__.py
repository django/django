from django.core.validators import ValidationError
from django.oldforms import LargeTextField
from django.contrib.gis.geos import GEOSException, GEOSGeometry

class WKTField(LargeTextField):
    "An oldforms LargeTextField for editing WKT text in the admin."
    def __init__(self, *args, **kwargs):
        super(WKTField, self).__init__(*args, **kwargs)
        # Overridding the validator list.
        self.validator_list = [self.isValidGeom]

    def render(self, data):
        # Returns the WKT value for the geometry field.  When no such data
        #  is present, return None to LargeTextField's render.
        if isinstance(data, GEOSGeometry):
            return super(WKTField, self).render(data.wkt)
        elif isinstance(data, basestring):
            return super(WKTField, self).render(data)
        else:
            return super(WKTField, self).render(None)

    def isValidGeom(self, field_data, all_data):
        try:
            g = GEOSGeometry(field_data)
        except GEOSException:
            raise ValidationError('Valid WKT or HEXEWKB is required for Geometry Fields.')
        
    
                                        
