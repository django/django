"""
Extracts the version of the PostgreSQL server.
"""

import re

# This reg-exp is intentionally fairly flexible here.
# Needs to be able to handle stuff like:
#   PostgreSQL #.#.#
#   EnterpriseDB #.#
#   PostgreSQL #.# beta#
#   PostgreSQL #.#beta#
VERSION_RE = re.compile(r'\S+ (\d+)\.(\d+)\.?(\d+)?')


def _parse_version(text):
    "Internal parsing method. Factored out for testing purposes."
    major, major2, minor = VERSION_RE.search(text).groups()
    try:
        return int(major) * 10000 + int(major2) * 100 + int(minor)
    except (ValueError, TypeError):
        return int(major) * 10000 + int(major2) * 100


def get_version(connection):
    """
    Returns an integer representing the major, minor and revision number of the
    server. Format is the one used for the return value of libpq
    PQServerVersion()/``server_version`` connection attribute (available in
    newer psycopg2 versions.)

    For example, 90304 for 9.3.4. The last two digits will be 00 in the case of
    releases (e.g., 90400 for 'PostgreSQL 9.4') or in the case of beta and
    prereleases (e.g. 90100 for 'PostgreSQL 9.1beta2').

    PQServerVersion()/``server_version`` doesn't execute a query so try that
    first, then fallback to a ``SELECT version()`` query.
    """
    if hasattr(connection, 'server_version'):
        return connection.server_version
    else:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            return _parse_version(cursor.fetchone()[0])
