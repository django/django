from thibaud.apps import AppConfig
from thibaud.core.signals import setting_changed
from thibaud.db import connections
from thibaud.db.backends.postgresql.psycopg_any import RANGE_TYPES
from thibaud.db.backends.signals import connection_created
from thibaud.db.migrations.writer import MigrationWriter
from thibaud.db.models import CharField, OrderBy, TextField
from thibaud.db.models.functions import Collate
from thibaud.db.models.indexes import IndexExpression
from thibaud.utils.translation import gettext_lazy as _

from .indexes import OpClass
from .lookups import (
    SearchLookup,
    TrigramSimilar,
    TrigramStrictWordSimilar,
    TrigramWordSimilar,
    Unaccent,
)
from .serializers import RangeSerializer
from .signals import register_type_handlers


def uninstall_if_needed(setting, value, enter, **kwargs):
    """
    Undo the effects of PostgresConfig.ready() when thibaud.contrib.postgres
    is "uninstalled" by override_settings().
    """
    if (
        not enter
        and setting == "INSTALLED_APPS"
        and "thibaud.contrib.postgres" not in set(value)
    ):
        connection_created.disconnect(register_type_handlers)
        CharField._unregister_lookup(Unaccent)
        TextField._unregister_lookup(Unaccent)
        CharField._unregister_lookup(SearchLookup)
        TextField._unregister_lookup(SearchLookup)
        CharField._unregister_lookup(TrigramSimilar)
        TextField._unregister_lookup(TrigramSimilar)
        CharField._unregister_lookup(TrigramWordSimilar)
        TextField._unregister_lookup(TrigramWordSimilar)
        CharField._unregister_lookup(TrigramStrictWordSimilar)
        TextField._unregister_lookup(TrigramStrictWordSimilar)
        # Disconnect this receiver until the next time this app is installed
        # and ready() connects it again to prevent unnecessary processing on
        # each setting change.
        setting_changed.disconnect(uninstall_if_needed)
        MigrationWriter.unregister_serializer(RANGE_TYPES)


class PostgresConfig(AppConfig):
    name = "thibaud.contrib.postgres"
    verbose_name = _("PostgreSQL extensions")

    def ready(self):
        setting_changed.connect(uninstall_if_needed)
        # Connections may already exist before we are called.
        for conn in connections.all(initialized_only=True):
            if conn.vendor == "postgresql":
                conn.introspection.data_types_reverse.update(
                    {
                        3904: "thibaud.contrib.postgres.fields.IntegerRangeField",
                        3906: "thibaud.contrib.postgres.fields.DecimalRangeField",
                        3910: "thibaud.contrib.postgres.fields.DateTimeRangeField",
                        3912: "thibaud.contrib.postgres.fields.DateRangeField",
                        3926: "thibaud.contrib.postgres.fields.BigIntegerRangeField",
                    }
                )
                if conn.connection is not None:
                    register_type_handlers(conn)
        connection_created.connect(register_type_handlers)
        CharField.register_lookup(Unaccent)
        TextField.register_lookup(Unaccent)
        CharField.register_lookup(SearchLookup)
        TextField.register_lookup(SearchLookup)
        CharField.register_lookup(TrigramSimilar)
        TextField.register_lookup(TrigramSimilar)
        CharField.register_lookup(TrigramWordSimilar)
        TextField.register_lookup(TrigramWordSimilar)
        CharField.register_lookup(TrigramStrictWordSimilar)
        TextField.register_lookup(TrigramStrictWordSimilar)
        MigrationWriter.register_serializer(RANGE_TYPES, RangeSerializer)
        IndexExpression.register_wrappers(OrderBy, OpClass, Collate)
