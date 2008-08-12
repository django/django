"""
Extracts the version of the PostgreSQL server.
"""

import re

VERSION_RE = re.compile(r'PostgreSQL (\d+)\.(\d+)\.')

def get_version(cursor):
    """
    Returns a tuple representing the major and minor version number of the
    server. For example, (7, 4) or (8, 3).
    """
    cursor.execute("SELECT version()")
    version = cursor.fetchone()[0]
    major, minor = VERSION_RE.search(version).groups()
    return int(major), int(minor)

