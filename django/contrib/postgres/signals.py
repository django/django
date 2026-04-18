import functools

from django.db import connections
from django.db.backends.base.base import NO_DB_ALIAS
from django.db.backends.postgresql.psycopg_any import is_psycopg3


def get_type_oids(connection_alias, type_name):
    with connections[connection_alias].cursor() as cursor:
        cursor.execute(
            "SELECT oid, typarray FROM pg_type WHERE typname = %s", (type_name,)
        )
        oids = []
        array_oids = []
        for row in cursor:
            oids.append(row[0])
            array_oids.append(row[1])
        return tuple(oids), tuple(array_oids)


@functools.lru_cache
def get_hstore_oids(connection_alias):
    """Return hstore and hstore array OIDs."""
    return get_type_oids(connection_alias, "hstore")


@functools.lru_cache
def get_citext_oids(connection_alias):
    """Return citext and citext array OIDs."""
    return get_type_oids(connection_alias, "citext")


if is_psycopg3:
    from psycopg.types import TypeInfo, hstore

    def register_type_handlers(connection, **kwargs):
        if connection.vendor != "postgresql" or connection.alias == NO_DB_ALIAS:
            return

        oids, array_oids = get_hstore_oids(connection.alias)
        for oid, array_oid in zip(oids, array_oids):
            ti = TypeInfo("hstore", oid, array_oid)
            hstore.register_hstore(ti, connection.connection)

        _, citext_oids = get_citext_oids(connection.alias)
        for array_oid in citext_oids:
            ti = TypeInfo("citext", 0, array_oid)
            ti.register(connection.connection)

else:
    import psycopg2
    from psycopg2.extras import register_hstore

    def register_type_handlers(connection, **kwargs):
        if connection.vendor != "postgresql" or connection.alias == NO_DB_ALIAS:
            return

        oids, array_oids = get_hstore_oids(connection.alias)
        # Don't register handlers when hstore is not available on the database.
        #
        # If someone tries to create an hstore field it will error there. This
        # is necessary as someone may be using PSQL without extensions
        # installed but be using other features of contrib.postgres.
        #
        # This is also needed in order to create the connection in order to
        # install the hstore extension.
        if oids:
            register_hstore(
                connection.connection, globally=True, oid=oids, array_oid=array_oids
            )

        oids, citext_oids = get_citext_oids(connection.alias)
        # Don't register handlers when citext is not available on the database.
        #
        # The same comments in the above call to register_hstore() also apply
        # here.
        if oids:
            array_type = psycopg2.extensions.new_array_type(
                citext_oids, "citext[]", psycopg2.STRING
            )
            psycopg2.extensions.register_type(array_type, None)
