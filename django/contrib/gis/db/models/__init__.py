from django.core.exceptions import ImproperlyConfigured

# Want to get everything from the 'normal' models package.
from django.db.models import *  # NOQA
from django.utils.version import get_docs_version

from django.contrib.gis.geos import HAS_GEOS

if not HAS_GEOS:
    raise ImproperlyConfigured(
        "GEOS is required and has not been detected. Are you sure it is installed? "
        "See also https://docs.djangoproject.com/en/%s/ref/contrib/gis/install/geolibs/" % get_docs_version())

# Geographic aggregate functions
from django.contrib.gis.db.models.aggregates import *  # NOQA

# The GeoManager
from django.contrib.gis.db.models.manager import GeoManager  # NOQA

# The geographic-enabled fields.
from django.contrib.gis.db.models.fields import (  # NOQA
    GeometryField, PointField, LineStringField, PolygonField,
    MultiPointField, MultiLineStringField, MultiPolygonField,
    GeometryCollectionField)
