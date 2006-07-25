from django.db import models
from django.db.backends.ansi.sql import BoundStatement, SchemaBuilder, \
    default_style

class PgSchemaBuilder(SchemaBuilder):
    """SchemaBuilder for postgres. Implements an additional method that
    outputs SQL statements to reset the sequence(s) for a model.
    """
    def get_sequence_reset(self, model, style=None):
        """Get sequence reset sql for a model.
        """
        if style is None:
            style=default_style
        for f in model._meta.fields:
            output = []
            db = model._default_manager.db
            connection = db.connection
            qn = db.backend.quote_name
            if isinstance(f, models.AutoField):
                output.append(BoundStatement(
                        "%s setval('%s', (%s max(%s) %s %s));" % \
                        (style.SQL_KEYWORD('SELECT'),
                         style.SQL_FIELD('%s_%s_seq' %
                                         (model._meta.db_table, f.column)),
                         style.SQL_KEYWORD('SELECT'),
                         style.SQL_FIELD(qn(f.column)),
                         style.SQL_KEYWORD('FROM'),
                         style.SQL_TABLE(qn(model._meta.db_table))),
                        connection))
                break # Only one AutoField is allowed per model, so don't bother continuing.
        for f in model._meta.many_to_many:
            output.append(
                BoundStatement("%s setval('%s', (%s max(%s) %s %s));" % \
                               (style.SQL_KEYWORD('SELECT'),
                                style.SQL_FIELD('%s_id_seq' % f.m2m_db_table()),
                                style.SQL_KEYWORD('SELECT'),
                                style.SQL_FIELD(qn('id')),
                                style.SQL_KEYWORD('FROM'),
                                style.SQL_TABLE(f.m2m_db_table())),
                               connection))
        return output
