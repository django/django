"""
Extracts the version of the PostgreSQL server.
"""

import re

# This reg-exp is intentionally fairly flexible here.
# Needs to be able to handle stuff like:
#   PostgreSQL 8.3.6
#   EnterpriseDB 8.3
#   PostgreSQL 8.3 beta4
#   PostgreSQL 8.4beta1
VERSION_RE = re.compile(r'\S+ (\d+)\.(\d+)\.?(\d+)?')

def _parse_version(text):
    "Internal parsing method. Factored out for testing purposes."
    major, major2, minor = VERSION_RE.search(text).groups()
    try:
        return int(major), int(major2), int(minor)
    except (ValueError, TypeError):
        return int(major), int(major2), None

def get_version(cursor):
    """
    Returns a tuple representing the major, minor and revision number of the
    server. For example, (7, 4, 1) or (8, 3, 4). The revision number will be
    None in the case of initial releases (e.g., 'PostgreSQL 8.3') or in the
    case of beta and prereleases ('PostgreSQL 8.4beta1').
    """
    cursor.execute("SELECT version()")
    return _parse_version(cursor.fetchone()[0])
