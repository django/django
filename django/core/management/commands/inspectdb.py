from __future__ import unicode_literals

import keyword
import re
from collections import OrderedDict

from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections


class Command(BaseCommand):
    help = "Introspects the database tables in the given database and outputs a Django model module."

    requires_system_checks = False

    db_module = 'django.db'

    def add_arguments(self, parser):
        parser.add_argument('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to '
            'introspect. Defaults to using the "default" database.')

    def handle(self, **options):
        try:
            for line in self.handle_inspection(options):
                self.stdout.write("%s\n" % line)
        except NotImplementedError:
            raise CommandError("Database inspection isn't supported for the currently selected database backend.")

    def handle_inspection(self, options):
        connection = connections[options['database']]
        # 'table_name_filter' is a stealth option
        table_name_filter = options.get('table_name_filter')

        table2model = lambda table_name: re.sub(r'[^a-zA-Z0-9]', '', table_name.title())
        strip_prefix = lambda s: s[1:] if s.startswith("u'") else s

        with connection.cursor() as cursor:
            yield "# This is an auto-generated Django model module."
            yield "# You'll have to do the following manually to clean this up:"
            yield "#   * Rearrange models' order"
            yield "#   * Make sure each model has one field with primary_key=True"
            yield (
                "#   * Remove `managed = False` lines if you wish to allow "
                "Django to create, modify, and delete the table"
            )
            yield "# Feel free to rename the models, but don't rename db_table values or field names."
            yield "#"
            yield "# Also note: You'll have to insert the output of 'django-admin sqlcustom [app_label]'"
            yield "# into your database."
            yield "from __future__ import unicode_literals"
            yield ''
            yield 'from %s import models' % self.db_module
            known_models = []
            for table_name in connection.introspection.table_names(cursor):
                if table_name_filter is not None and callable(table_name_filter):
                    if not table_name_filter(table_name):
                        continue
                yield ''
                yield ''
                yield 'class %s(models.Model):' % table2model(table_name)
                known_models.append(table2model(table_name))
                try:
                    relations = connection.introspection.get_relations(cursor, table_name)
                except NotImplementedError:
                    relations = {}
                try:
                    indexes = connection.introspection.get_indexes(cursor, table_name)
                except NotImplementedError:
                    indexes = {}
                try:
                    constraints = connection.introspection.get_constraints(cursor, table_name)
                except NotImplementedError:
                    constraints = {}
                used_column_names = []  # Holds column names used in the table so far
                for row in connection.introspection.get_table_description(cursor, table_name):
                    comment_notes = []  # Holds Field notes, to be displayed in a Python comment.
                    extra_params = OrderedDict()  # Holds Field parameters such as 'db_column'.
                    column_name = row[0]
                    is_relation = column_name in relations

                    att_name, params, notes = self.normalize_col_name(
                        column_name, used_column_names, is_relation)
                    extra_params.update(params)
                    comment_notes.extend(notes)

                    used_column_names.append(att_name)

                    # Add primary_key and unique, if necessary.
                    if column_name in indexes:
                        if indexes[column_name]['primary_key']:
                            extra_params['primary_key'] = True
                        elif indexes[column_name]['unique']:
                            extra_params['unique'] = True

                    if is_relation:
                        rel_to = "self" if relations[column_name][1] == table_name else table2model(relations[column_name][1])
                        if rel_to in known_models:
                            field_type = 'ForeignKey(%s' % rel_to
                        else:
                            field_type = "ForeignKey('%s'" % rel_to
                    else:
                        # Calling `get_field_type` to get the field type string and any
                        # additional parameters and notes.
                        field_type, field_params, field_notes = self.get_field_type(connection, table_name, row)
                        extra_params.update(field_params)
                        comment_notes.extend(field_notes)

                        field_type += '('

                    # Don't output 'id = meta.AutoField(primary_key=True)', because
                    # that's assumed if it doesn't exist.
                    if att_name == 'id' and extra_params == {'primary_key': True}:
                        if field_type == 'AutoField(':
                            continue
                        elif field_type == 'IntegerField(' and not connection.features.can_introspect_autofield:
                            comment_notes.append('AutoField?')

                    # Add 'null' and 'blank', if the 'null_ok' flag was present in the
                    # table description.
                    if row[6]:  # If it's NULL...
                        if field_type == 'BooleanField(':
                            field_type = 'NullBooleanField('
                        else:
                            extra_params['blank'] = True
                            extra_params['null'] = True

                    field_desc = '%s = %s%s' % (
                        att_name,
                        # Custom fields will have a dotted path
                        '' if '.' in field_type else 'models.',
                        field_type,
                    )
                    if extra_params:
                        if not field_desc.endswith('('):
                            field_desc += ', '
                        field_desc += ', '.join(
                            '%s=%s' % (k, strip_prefix(repr(v)))
                            for k, v in extra_params.items())
                    field_desc += ')'
                    if comment_notes:
                        field_desc += '  # ' + ' '.join(comment_notes)
                    yield '    %s' % field_desc
                for meta_line in self.get_meta(table_name, constraints):
                    yield meta_line

    def normalize_col_name(self, col_name, used_column_names, is_relation):
        """
        Modify the column name to make it Python-compatible as a field name
        """
        field_params = {}
        field_notes = []

        new_name = col_name.lower()
        if new_name != col_name:
            field_notes.append('Field name made lowercase.')

        if is_relation:
            if new_name.endswith('_id'):
                new_name = new_name[:-3]
            else:
                field_params['db_column'] = col_name

        new_name, num_repl = re.subn(r'\W', '_', new_name)
        if num_repl > 0:
            field_notes.append('Field renamed to remove unsuitable characters.')

        if new_name.find('__') >= 0:
            while new_name.find('__') >= 0:
                new_name = new_name.replace('__', '_')
            if col_name.lower().find('__') >= 0:
                # Only add the comment if the double underscore was in the original name
                field_notes.append("Field renamed because it contained more than one '_' in a row.")

        if new_name.startswith('_'):
            new_name = 'field%s' % new_name
            field_notes.append("Field renamed because it started with '_'.")

        if new_name.endswith('_'):
            new_name = '%sfield' % new_name
            field_notes.append("Field renamed because it ended with '_'.")

        if keyword.iskeyword(new_name):
            new_name += '_field'
            field_notes.append('Field renamed because it was a Python reserved word.')

        if new_name[0].isdigit():
            new_name = 'number_%s' % new_name
            field_notes.append("Field renamed because it wasn't a valid Python identifier.")

        if new_name in used_column_names:
            num = 0
            while '%s_%d' % (new_name, num) in used_column_names:
                num += 1
            new_name = '%s_%d' % (new_name, num)
            field_notes.append('Field renamed because of name conflict.')

        if col_name != new_name and field_notes:
            field_params['db_column'] = col_name

        return new_name, field_params, field_notes

    def get_field_type(self, connection, table_name, row):
        """
        Given the database connection, the table name, and the cursor row
        description, this routine will return the given field type name, as
        well as any additional keyword parameters and notes for the field.
        """
        field_params = OrderedDict()
        field_notes = []

        try:
            field_type = connection.introspection.get_field_type(row[1], row)
        except KeyError:
            field_type = 'TextField'
            field_notes.append('This field type is a guess.')

        # This is a hook for data_types_reverse to return a tuple of
        # (field_type, field_params_dict).
        if type(field_type) is tuple:
            field_type, new_params = field_type
            field_params.update(new_params)

        # Add max_length for all CharFields.
        if field_type == 'CharField' and row[3]:
            field_params['max_length'] = int(row[3])

        if field_type == 'DecimalField':
            if row[4] is None or row[5] is None:
                field_notes.append(
                    'max_digits and decimal_places have been guessed, as this '
                    'database handles decimal fields as float')
                field_params['max_digits'] = row[4] if row[4] is not None else 10
                field_params['decimal_places'] = row[5] if row[5] is not None else 5
            else:
                field_params['max_digits'] = row[4]
                field_params['decimal_places'] = row[5]

        return field_type, field_params, field_notes

    def get_meta(self, table_name, constraints):
        """
        Return a sequence comprising the lines of code necessary
        to construct the inner Meta class for the model corresponding
        to the given database table name.
        """
        unique_together = []
        for index, params in constraints.items():
            if params['unique']:
                columns = params['columns']
                if len(columns) > 1:
                    # we do not want to include the u"" or u'' prefix
                    # so we build the string rather than interpolate the tuple
                    tup = '(' + ', '.join("'%s'" % c for c in columns) + ')'
                    unique_together.append(tup)
        meta = ["",
                "    class Meta:",
                "        managed = False",
                "        db_table = '%s'" % table_name]
        if unique_together:
            tup = '(' + ', '.join(unique_together) + ',)'
            meta += ["        unique_together = %s" % tup]
        return meta
