"""
Extracts the version of the PostgreSQL server.
"""

import re

# This reg-exp is intentionally fairly flexible here. Require only the major
# and minor version numbers, but need to be able to handle standard stuff like:
#   PostgreSQL 8.3.6
#   EnterpriseDB 8.3
#   PostgreSQL 8.3 beta4
VERSION_RE = re.compile(r'\S+ (\d+)\.(\d+)')

def get_version(cursor):
    """
    Returns a tuple representing the major and minor version number of the
    server. For example, (7, 4) or (8, 3).
    """
    cursor.execute("SELECT version()")
    version = cursor.fetchone()[0]
    major, minor = VERSION_RE.search(version).groups()
    return int(major), int(minor)

