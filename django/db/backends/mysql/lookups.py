from django.db.models import Field
from django.db.models.lookups import Contains, EndsWith, StartsWith

BINARY_CAST = "CAST({} AS BINARY)"


class _BinaryCollationMixin:
    """
    Force case-sensitive semantics by applying a binary collation to both
    LHS and RHS. If we cannot determine a suitable collation, fall back to
    CAST(... AS BINARY) on both sides (keeps correctness).
    """

    def process_lhs(self, compiler, connection, lhs=None):
        lhs_sql, lhs_params = super().process_lhs(compiler, connection, lhs)
        collate = getattr(connection.ops, "collate_binary_sql", None)
        if collate:
            lhs_sql = connection.ops.collate_binary_sql(lhs_sql)
        else:
            lhs_sql = BINARY_CAST.format(lhs_sql)
        return lhs_sql, lhs_params

    def process_rhs(self, compiler, connection):
        rhs_sql, rhs_params = super().process_rhs(compiler, connection)
        collate = getattr(connection.ops, "collate_binary_sql", None)
        if collate:
            rhs_sql = connection.ops.collate_binary_sql(rhs_sql)
        else:
            rhs_sql = BINARY_CAST.format(rhs_sql)
        return rhs_sql, rhs_params


class MySQLContains(_BinaryCollationMixin, Contains):
    pass


class MySQLStartsWith(_BinaryCollationMixin, StartsWith):
    pass


class MySQLEndsWith(_BinaryCollationMixin, EndsWith):
    pass


# Register on the base Field so it applies broadly (CharField, TextField,
# UUID casts, JSON key transforms that become text, etc.)
Field.register_lookup(MySQLContains)
Field.register_lookup(MySQLStartsWith)
Field.register_lookup(MySQLEndsWith)
