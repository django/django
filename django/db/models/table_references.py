from django.db import NotSupportedError
from django.utils.deconstruct import deconstructible


@deconstructible(path="django.db.models.SchemaQualifiedTable")
class SchemaQualifiedTable:
    """
    A schema-qualified database table reference.

    This renders table references such as:

        "billing"."customer"

    on backends that support schema-qualified table references.
    """

    always_alias = True

    def __init__(self, table, *, schema):
        if not isinstance(table, str) or not table:
            raise ValueError("table must be a non-empty string.")
        if not isinstance(schema, str) or not schema:
            raise ValueError("schema must be a non-empty string.")
        self.table = table
        self.schema = schema

    @property
    def identity(self):
        return self.__class__, self.schema, self.table

    def as_sql_name(self, connection):
        if not connection.features.supports_schema_qualified_table_references:
            raise NotSupportedError(
                "%s doesn't support schema-qualified table references."
                % connection.display_name
            )
        qn = connection.ops.quote_name
        return "%s.%s" % (qn(self.schema), qn(self.table))

    def as_sql(self, compiler, connection):
        return self.as_sql_name(connection), []

    def __repr__(self):
        return "%s(%r, schema=%r)" % (
            self.__class__.__name__,
            self.table,
            self.schema,
        )

    def __eq__(self, other):
        if not isinstance(other, SchemaQualifiedTable):
            return NotImplemented
        return self.identity == other.identity

    def __hash__(self):
        return hash(self.identity)
