import psycopg2
from psycopg2 import ProgrammingError
from psycopg2.extras import register_hstore

from django.utils import six


def register_type_handlers(connection, **kwargs):
    if connection.vendor != 'postgresql':
        return

    try:
        if six.PY2:
            register_hstore(connection.connection, globally=True, unicode=True)
        else:
            register_hstore(connection.connection, globally=True)
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
        with connection.cursor() as cursor:
            # Retrieve oids of citext arrays.
            cursor.execute("SELECT typarray FROM pg_type WHERE typname = 'citext'")
            oids = tuple(row[0] for row in cursor)
        array_type = psycopg2.extensions.new_array_type(oids, 'citext[]', psycopg2.STRING)
        psycopg2.extensions.register_type(array_type, None)
    except ProgrammingError:
        # citext is not available on the database.
        #
        # The same comments in the except block of the above call to
        # register_hstore() also apply here.
        pass
