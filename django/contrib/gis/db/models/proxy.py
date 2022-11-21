"""
The SpatialProxy object allows for lazy-geometries and lazy-rasters. The proxy
uses Python descriptors for instantiating and setting Geometry or Raster
objects corresponding to geographic model fields.

Thanks to Robert Coup for providing this functionality (see #4322).
"""
from django.db.models.query_utils import DeferredAttribute


class SpatialProxy(DeferredAttribute):
    def __init__(self, klass, field, load_func=None):
        """
        Initialize on the given Geometry or Raster class (not an instance)
        and the corresponding field.
        """
        self._klass = klass
        self._load_func = load_func or klass
        super().__init__(field)

    def __get__(self, instance, cls=None):
        """
        Retrieve the geometry or raster, initializing it using the
        corresponding class specified during initialization and the value of
        the field. Currently, GEOS or OGR geometries as well as GDALRasters are
        supported.
        """
        if instance is None:
            # Accessed on a class, not an instance
            return self

        # Getting the value of the field.
        try:
            geo_value = instance.__dict__[self.field.attname]
        except KeyError:
            geo_value = super().__get__(instance, cls)

        if isinstance(geo_value, self._klass):
            geo_obj = geo_value
        elif (geo_value is None) or (geo_value == ""):
            geo_obj = None
        else:
            # Otherwise, a geometry or raster object is built using the field's
            # contents, and the model's corresponding attribute is set.
            geo_obj = self._load_func(geo_value)
            setattr(instance, self.field.attname, geo_obj)
        return geo_obj

    def __set__(self, instance, value):
        """
        Retrieve the proxied geometry or raster with the corresponding class
        specified during initialization.

        To set geometries, use values of None, HEXEWKB, or WKT.
        To set rasters, use JSON or dict values.
        """
        # The geographic type of the field.
        gtype = self.field.geom_type

        if gtype == "RASTER" and (
            value is None or isinstance(value, (str, dict, self._klass))
        ):
            # For raster fields, ensure input is None or a string, dict, or
            # raster instance.
            pass
        elif isinstance(value, self._klass):
            # The geometry type must match that of the field -- unless the
            # general GeometryField is used.
            if value.srid is None:
                # Assigning the field SRID if the geometry has no SRID.
                value.srid = self.field.srid
        elif value is not None and not isinstance(value, (str, memoryview)):
            raise TypeError(
                f"Cannot set {instance.__class__.__name__} SpatialProxy ({gtype}) with value of type: {type(value)}"
            )


        # Setting the objects dictionary with the value, and returning.
        instance.__dict__[self.field.attname] = value
        return value
