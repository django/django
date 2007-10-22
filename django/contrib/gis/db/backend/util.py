class GeoFieldSQL(object):
    """
    Container for passing values to `parse_lookup` from the various
    backend geometry fields.
    """
    def __init__(self, where=[], params=[]):
        self.where = where
        self.params = params

def get_srid(field, geom):
    """
    Gets the SRID depending on the value of the SRID setting of the field
    and that of the given geometry.
    """
    if geom.srid is None or (geom.srid == -1 and field._srid != -1):
        return field._srid
    else:
        return geom.srid
