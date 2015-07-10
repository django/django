from django.db.models.sql import aggregates
from django.db.models.sql.aggregates import *  # NOQA

__all__ = ['Collect', 'Extent', 'Extent3D', 'MakeLine', 'Union'] + aggregates.__all__


warnings.warn(
    "django.contrib.gis.db.models.sql.aggregates is deprecated. Use "
    "django.contrib.gis.db.models.aggregates instead.",
    RemovedInDjango110Warning, stacklevel=2)
