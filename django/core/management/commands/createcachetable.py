from optparse import make_option

from django.core.management.base import LabelCommand
from django.db import connections, transaction, models, DEFAULT_DB_ALIAS

class Command(LabelCommand):
    help = "Creates the table needed to use the SQL cache backend."
    args = "<tablename>"
    label = 'tablename'

    option_list = LabelCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database onto '
                'which the cache table will be installed. '
                'Defaults to the "default" database.'),
    )

    requires_model_validation = False

    def handle_label(self, tablename, **options):
        alias = options.get('database', DEFAULT_DB_ALIAS)
        connection = connections[alias]
        fields = (
            # "key" is a reserved word in MySQL, so use "cache_key" instead.
            models.CharField(name='cache_key', max_length=255, unique=True, primary_key=True),
            models.TextField(name='value'),
            models.DateTimeField(name='expires', db_index=True),
        )
        table_output = []
        index_output = []
        qn = connection.ops.quote_name
        for f in fields:
            field_output = [qn(f.name), f.db_type(connection=connection)]
            field_output.append("%sNULL" % (not f.null and "NOT " or ""))
            if f.primary_key:
                field_output.append("PRIMARY KEY")
            elif f.unique:
                field_output.append("UNIQUE")
            if f.db_index:
                unique = f.unique and "UNIQUE " or ""
                index_output.append("CREATE %sINDEX %s_%s ON %s (%s);" % \
                    (unique, tablename, f.name, qn(tablename),
                    qn(f.name)))
            table_output.append(" ".join(field_output))
        full_statement = ["CREATE TABLE %s (" % qn(tablename)]
        for i, line in enumerate(table_output):
            full_statement.append('    %s%s' % (line, i < len(table_output)-1 and ',' or ''))
        full_statement.append(');')
        curs = connection.cursor()
        curs.execute("\n".join(full_statement))
        for statement in index_output:
            curs.execute(statement)
        transaction.commit_unless_managed(using=alias)
