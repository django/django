from django.apps import AppConfig
from django.db import connections
from django.db.backends.signals import connection_created
from django.db.models import CharField, TextField
from django.utils.translation import gettext_lazy as _

from .lookups import SearchLookup, TrigramSimilar, Unaccent
from .signals import register_hstore_handler


class PostgresConfig(AppConfig):
    name = 'django.contrib.postgres'
    verbose_name = _('PostgreSQL extensions')

    def ready(self):
        # Connections may already exist before we are called.
        for conn in connections.all():
            if conn.connection is not None:
                register_hstore_handler(conn)
        connection_created.connect(register_hstore_handler)
        CharField.register_lookup(Unaccent)
        TextField.register_lookup(Unaccent)
        CharField.register_lookup(SearchLookup)
        TextField.register_lookup(SearchLookup)
        CharField.register_lookup(TrigramSimilar)
        TextField.register_lookup(TrigramSimilar)
