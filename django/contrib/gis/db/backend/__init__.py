from django.db import connection

if hasattr(connection.ops, 'spatial_version'):
    from warnings import warn
    warn('The `django.contrib.gis.db.backend` module was refactored and '
         'renamed to `django.contrib.gis.db.backends` in 1.2.  '
         'All functionality of `SpatialBackend` '
         'has been moved to the `ops` attribute of the spatial database '
         'backend.  A `SpatialBackend` alias is provided here for '
         'backwards-compatibility, but will be removed in 1.3.')
    SpatialBackend = connection.ops

from django.db import connection

if hasattr(connection.ops, 'spatial_version'):
    from warnings import warn
    warn('The `django.contrib.gis.db.backend` module was refactored and '
         'renamed to `django.contrib.gis.db.backends` in 1.2.  '
         'All functionality of `SpatialBackend` '
         'has been moved to the `ops` attribute of the spatial database '
         'backend.  A `SpatialBackend` alias is provided here for '
         'backwards-compatibility, but will be removed in 1.3.')
    SpatialBackend = connection.ops

