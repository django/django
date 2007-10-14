class GeoFieldSQL(object):
    """
    Container for passing values to `parse_lookup` from the various
    backend geometry fields.
    """
    def __init__(self, where=[], params=[]):
        self.where = where
        self.params = params
