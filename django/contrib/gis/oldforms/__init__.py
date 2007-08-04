from django.oldforms import LargeTextField

class WKTField(LargeTextField):
    "An oldforms LargeTextField for editing WKT text in the admin."
    
    def render(self, data):
        # Returns the WKT value for the geometry field.  When no such data
        #  is present, return None to LargeTextField's render.
        if not data:
            return super(WKTField, self).render(None)
        else:
            return super(WKTField, self).render(data.wkt)
    
                                        
