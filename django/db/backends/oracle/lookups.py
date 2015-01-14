"""
Oracle-specific lookups
"""
from __future__ import unicode_literals

from django.db.models import TextField

Contains = TextField._get_lookup('contains')


class OracleContains(Contains):
    """
    Oracle uses 'CONTAINS' for contains queries on LOBs
    """
    def as_oracle(self, compiler, connection):
        # We need to ignore the default rules for processing the LHS
        lhs, lhs_params = compiler.compile(self.lhs)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        return "DBMS_LOB.INSTR ({0}, {1}) > 0".format(lhs, rhs), (lhs_params + rhs_params)

    def get_db_prep_lookup(self, value, connection):
        # Undo the default behavior for contains
        return ('%s', [value])

TextField.register_lookup(OracleContains)
