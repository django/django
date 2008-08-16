from django.core.management.base import NoArgsCommand, CommandError

class Command(NoArgsCommand):
    help = "Introspects the database tables in the given database and outputs a Django model module."

    requires_model_validation = False

    def handle_noargs(self, **options):
        try:
            for line in self.handle_inspection():
                print line
        except NotImplementedError:
            raise CommandError("Database inspection isn't supported for the currently selected database backend.")

    def handle_inspection(self):
        from django.db import connection
        import keyword

        table2model = lambda table_name: table_name.title().replace('_', '').replace(' ', '').replace('-', '')

        cursor = connection.cursor()
        yield "# This is an auto-generated Django model module."
        yield "# You'll have to do the following manually to clean this up:"
        yield "#     * Rearrange models' order"
        yield "#     * Make sure each model has one field with primary_key=True"
        yield "# Feel free to rename the models, but don't rename db_table values or field names."
        yield "#"
        yield "# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [appname]'"
        yield "# into your database."
        yield ''
        yield 'from django.db import models'
        yield ''
        for table_name in connection.introspection.get_table_list(cursor):
            yield 'class %s(models.Model):' % table2model(table_name)
            try:
                relations = connection.introspection.get_relations(cursor, table_name)
            except NotImplementedError:
                relations = {}
            try:
                indexes = connection.introspection.get_indexes(cursor, table_name)
            except NotImplementedError:
                indexes = {}
            for i, row in enumerate(connection.introspection.get_table_description(cursor, table_name)):
                att_name = row[0].lower()
                comment_notes = [] # Holds Field notes, to be displayed in a Python comment.
                extra_params = {}  # Holds Field parameters such as 'db_column'.

                # If we need to do field name modifiations, 
                # remember the original field name
                if ' ' in att_name or '-' in att_name or keyword.iskeyword(att_name):
                    extra_params['db_column'] = att_name
                  
                # Now modify the field name to make it python compatible.  
                if ' ' in att_name:
                    att_name = att_name.replace(' ', '_')
                    comment_notes.append('Field renamed to remove spaces.')
                if '-' in att_name:
                    att_name = att_name.replace('-', '_')
                    comment_notes.append('Field renamed to remove dashes.')
                if keyword.iskeyword(att_name):
                    att_name += '_field'
                    comment_notes.append('Field renamed because it was a Python reserved word.')

                if i in relations:
                    rel_to = relations[i][1] == table_name and "'self'" or table2model(relations[i][1])
                    field_type = 'ForeignKey(%s' % rel_to
                    if att_name.endswith('_id'):
                        att_name = att_name[:-3]
                    else:
                        extra_params['db_column'] = att_name
                else:
                    try:
                        field_type = connection.introspection.data_types_reverse[row[1]]
                    except KeyError:
                        field_type = 'TextField'
                        comment_notes.append('This field type is a guess.')

                    # This is a hook for DATA_TYPES_REVERSE to return a tuple of
                    # (field_type, extra_params_dict).
                    if type(field_type) is tuple:
                        field_type, new_params = field_type
                        extra_params.update(new_params)

                    # Add max_length for all CharFields.
                    if field_type == 'CharField' and row[3]:
                        extra_params['max_length'] = row[3]

                    if field_type == 'DecimalField':
                        extra_params['max_digits'] = row[4]
                        extra_params['decimal_places'] = row[5]

                    # Add primary_key and unique, if necessary.
                    column_name = extra_params.get('db_column', att_name)
                    if column_name in indexes:
                        if indexes[column_name]['primary_key']:
                            extra_params['primary_key'] = True
                        elif indexes[column_name]['unique']:
                            extra_params['unique'] = True

                    field_type += '('

                # Don't output 'id = meta.AutoField(primary_key=True)', because
                # that's assumed if it doesn't exist.
                if att_name == 'id' and field_type == 'AutoField(' and extra_params == {'primary_key': True}:
                    continue

                # Add 'null' and 'blank', if the 'null_ok' flag was present in the
                # table description.
                if row[6]: # If it's NULL...
                    extra_params['blank'] = True
                    if not field_type in ('TextField(', 'CharField('):
                        extra_params['null'] = True

                field_desc = '%s = models.%s' % (att_name, field_type)
                if extra_params:
                    if not field_desc.endswith('('):
                        field_desc += ', '
                    field_desc += ', '.join(['%s=%r' % (k, v) for k, v in extra_params.items()])
                field_desc += ')'
                if comment_notes:
                    field_desc += ' # ' + ' '.join(comment_notes)
                yield '    %s' % field_desc
            yield '    class Meta:'
            yield '        db_table = %r' % table_name
            yield ''
