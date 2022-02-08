import functools

import psycopg2
from psycopg2 import ProgrammingError
from psycopg2.extras import register_hstore

from django.db import connections
from django.db.backends.base.base import NO_DB_ALIAS


@functools.lru_cache()
def get_hstore_oids(connection_alias):
    """Return hstore and hstore array OIDs."""
    with connections[connection_alias].cursor() as cursor:
        cursor.execute(
            "SELECT t.oid, typarray "
            "FROM pg_type t "
            "JOIN pg_namespace ns ON typnamespace = ns.oid "
            "WHERE typname = 'hstore'"
        )
        oids = []
        array_oids = []
        for row in cursor:
            oids.append(row[0])
            array_oids.append(row[1])
        return tuple(oids), tuple(array_oids)


@functools.lru_cache()
def get_citext_oids(connection_alias):
    """Return citext array OIDs."""
    with connections[connection_alias].cursor() as cursor:
        cursor.execute("SELECT typarray FROM pg_type WHERE typname = 'citext'")
        return tuple(row[0] for row in cursor)


def register_type_handlers(connection, **kwargs):
    if connection.vendor != "postgresql" or connection.alias == NO_DB_ALIAS:
        return

    try:
        oids, array_oids = get_hstore_oids(connection.alias)
        register_hstore(
            connection.connection, globally=True, oid=oids, array_oid=array_oids
        )
    except ProgrammingError:
        # Hstore is not available on the database.
        #
        # If someone tries to create an hstore field it will error there.
        # This is necessary as someone may be using PSQL without extensions
        # installed but be using other features of contrib.postgres.
        #
        # This is also needed in order to create the connection in order to
        # install the hstore extension.
        pass

    try:
        citext_oids = get_citext_oids(connection.alias)
        array_type = psycopg2.extensions.new_array_type(
            citext_oids, "citext[]", psycopg2.STRING
        )
        psycopg2.extensions.register_type(array_type, None)
    except ProgrammingError:
        # citext is not available on the database.
        #
        # The same comments in the except block of the above call to
        # register_hstore() also apply here.
        pass
