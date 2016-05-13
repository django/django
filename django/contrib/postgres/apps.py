from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.db.models import CharField, TextField
from django.utils.translation import ugettext_lazy as _

from .lookups import (
    DoubleMetaphone, Metaphone, SearchLookup, Soundex, Unaccent,
)
from .signals import register_hstore_handler


class PostgresConfig(AppConfig):
    name = 'django.contrib.postgres'
    verbose_name = _('PostgreSQL extensions')

    def ready(self):
        connection_created.connect(register_hstore_handler)
        CharField.register_lookup(Unaccent)
        TextField.register_lookup(Unaccent)
        CharField.register_lookup(SearchLookup)
        TextField.register_lookup(SearchLookup)
        CharField.register_lookup(DoubleMetaphone)
        TextField.register_lookup(DoubleMetaphone)
        CharField.register_lookup(Metaphone)
        TextField.register_lookup(Metaphone)
        CharField.register_lookup(Soundex)
        TextField.register_lookup(Soundex)
