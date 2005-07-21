"""
Helper functions for dictfetch* for databases that don't natively support them.
"""

def _dict_helper(desc, row):
    "Returns a dictionary for the given cursor.description and result row."
    return dict([(desc[col[0]][0], col[1]) for col in enumerate(row)])

def dictfetchone(cursor):
    "Returns a row from the cursor as a dict"
    row = cursor.fetchone()
    if not row:
        return None
    return _dict_helper(cursor.description, row)

def dictfetchmany(cursor, number):
    "Returns a certain number of rows from a cursor as a dict"
    desc = cursor.description
    return [_dict_helper(desc, row) for row in cursor.fetchmany(number)]

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [_dict_helper(desc, row) for row in cursor.fetchall()]
