class Default:
    """
    Expression for ``DEFAULT``.

    In an insert query this will return the database default.
    """

    def as_sql(self, compiler, connection):
        return connection.ops.pk_default_value(), []
