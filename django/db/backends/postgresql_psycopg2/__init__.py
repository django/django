import warnings

from django.utils.deprecation import RemovedInDjango30Warning

warnings.warn(
    "The django.db.backends.postgresql_psycopg2 module is deprecated in "
    "favor of django.db.backends.postgresql.",
    RemovedInDjango30Warning, stacklevel=2
)
