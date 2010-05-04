from django.db import connection

if (hasattr(connection.ops, 'spatial_version') and
    not connection.ops.mysql):
    # Getting the `SpatialRefSys` and `GeometryColumns`
    # models for the default spatial backend.  These
    # aliases are provided for backwards-compatibility.
    SpatialRefSys = connection.ops.spatial_ref_sys()
    GeometryColumns = connection.ops.geometry_columns()
