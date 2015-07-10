from psycopg2 import ProgrammingError
from psycopg2.extras import register_hstore

from django.utils import six


def register_hstore_handler(connection, **kwargs):
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
