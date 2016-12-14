from django.contrib.postgres.signals import register_hstore_handler
from django.db.migrations import RunSQL
from django.db.migrations.operations.base import Operation


class CreateExtension(Operation):
    reversible = True

    def __init__(self, name):
        self.name = name

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != 'postgresql':
            return
        schema_editor.execute("CREATE EXTENSION IF NOT EXISTS %s" % schema_editor.quote_name(self.name))

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        schema_editor.execute("DROP EXTENSION %s" % schema_editor.quote_name(self.name))

    def describe(self):
        return "Creates extension %s" % self.name


class BtreeGinExtension(CreateExtension):

    def __init__(self):
        self.name = 'btree_gin'


class CITextExtension(CreateExtension):

    def __init__(self):
        self.name = 'citext'


class CITextArrayGinOperatorClass(RunSQL):

    # SQL taken from
    # http://stackoverflow.com/questions/18082625/postgresql-9-2-gin-index-on-citext/20102665#20102665
    sql = """
        CREATE OPERATOR CLASS _citext_ops DEFAULT FOR TYPE citext[] USING gin AS
            OPERATOR        1       && (anyarray, anyarray),
            OPERATOR        4       = (anyarray, anyarray),
            OPERATOR        2       @> (anyarray, anyarray),
            OPERATOR        3       <@ (anyarray, anyarray),
            FUNCTION        1       citext_cmp (citext, citext),
            FUNCTION        2       ginarrayextract(anyarray, internal, internal),
            FUNCTION        3       ginqueryarrayextract(anyarray, internal, smallint, internal, internal,
                                                         internal, internal),
            FUNCTION        4       ginarrayconsistent(internal, smallint, anyarray, integer, internal, internal,
                                                       internal, internal),
            STORAGE         citext"""

    def __init__(self, sql=None, reverse_sql="DROP OPERATOR CLASS _citext_ops", **kwargs):
        super(CITextArrayGinOperatorClass, self).__init__(sql=self.sql, reverse_sql=reverse_sql, **kwargs)

    def describe(self):
        return "Creates an operator class for CIText for use in ArrayField"


class HStoreExtension(CreateExtension):

    def __init__(self):
        self.name = 'hstore'

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        super(HStoreExtension, self).database_forwards(app_label, schema_editor, from_state, to_state)
        # Register hstore straight away as it cannot be done before the
        # extension is installed, a subsequent data migration would use the
        # same connection
        register_hstore_handler(schema_editor.connection)


class TrigramExtension(CreateExtension):

    def __init__(self):
        self.name = 'pg_trgm'


class UnaccentExtension(CreateExtension):

    def __init__(self):
        self.name = 'unaccent'
