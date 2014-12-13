from django.db import connection

# Provide the `SpatialRefSys` and `GeometryColumns` models for the default
# spatial backend.
has_spatial = connection.features.gis_enabled and connection.features.has_spatialrefsys_table

SpatialRefSys = connection.ops.spatial_ref_sys() if has_spatial else None
GeometryColumns = connection.ops.geometry_columns() if has_spatial else None
