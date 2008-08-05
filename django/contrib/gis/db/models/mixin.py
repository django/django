# Until model subclassing is a possibility, a mixin class is used to add
# the necessary functions that may be contributed for geographic objects.
class GeoMixin:
    """
    The Geographic Mixin class provides routines for geographic objects,
    however, it is no longer necessary, since all of its previous functions 
    may now be accessed via the GeometryProxy.  This mixin is only provided
    for backwards-compatibility purposes, and will be eventually removed
    (unless the need arises again).
    """
    pass
