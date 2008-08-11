"""
 This overrides the traditional `inspectdb` command so that geographic databases
 may be introspected.
"""

from django.core.management.commands.inspectdb import Command as InspectCommand
from django.contrib.gis.db.backend import SpatialBackend

class Command(InspectCommand):

    # Mapping from lower-case OGC type to the corresponding GeoDjango field.
    geofield_mapping = {'point' : 'PointField',
                        'linestring' : 'LineStringField',
                        'polygon' : 'PolygonField',
                        'multipoint' : 'MultiPointField',
                        'multilinestring' : 'MultiLineStringField',
                        'multipolygon' : 'MultiPolygonField',
                        'geometrycollection' : 'GeometryCollectionField',
                        'geometry' : 'GeometryField',
                        }

    def geometry_columns(self):
        """
        Returns a datastructure of metadata information associated with the
        `geometry_columns` (or equivalent) table.
        """
        # The `geo_cols` is a dictionary data structure that holds information
        # about any geographic columns in the database.
        geo_cols = {}
        def add_col(table, column, coldata):
            if table in geo_cols:
                # If table already has a geometry column.
                geo_cols[table][column] = coldata
            else:
                # Otherwise, create a dictionary indexed by column.
                geo_cols[table] = { column : coldata }

        if SpatialBackend.name == 'postgis':
            # PostGIS holds all geographic column information in the `geometry_columns` table.
            from django.contrib.gis.models import GeometryColumns
            for geo_col in GeometryColumns.objects.all():
                table = geo_col.f_table_name
                column = geo_col.f_geometry_column
                coldata = {'type' : geo_col.type, 'srid' : geo_col.srid, 'dim' : geo_col.coord_dimension}
                add_col(table, column, coldata)
            return geo_cols
        elif SpatialBackend.name == 'mysql':
            # On MySQL have to get all table metadata before hand; this means walking through
            # each table and seeing if any column types are spatial.  Can't detect this with
            # `cursor.description` (what the introspection module does) because all spatial types
            # have the same integer type (255 for GEOMETRY).
            from django.db import connection
            cursor = connection.cursor()
            cursor.execute('SHOW TABLES')
            tables = cursor.fetchall();
            for table_tup in tables:
                table = table_tup[0]
                table_desc = cursor.execute('DESCRIBE `%s`' % table)
                col_info = cursor.fetchall()
                for column, typ, null, key, default, extra in col_info:
                    if typ in self.geofield_mapping: add_col(table, column, {'type' : typ})
            return geo_cols
        else:
            # TODO: Oracle (has incomplete `geometry_columns` -- have to parse
            #  SDO SQL to get specific type, SRID, and other information).
            raise NotImplementedError('Geographic database inspection not available.')

    def handle_inspection(self):
        "Overloaded from Django's version to handle geographic database tables."
        from django.db import connection
        import keyword

        geo_cols = self.geometry_columns()

        table2model = lambda table_name: table_name.title().replace('_', '')

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
        yield 'from django.contrib.gis.db import models'
        yield ''
        for table_name in connection.introspection.get_table_list(cursor):
            # Getting the geographic table dictionary.
            geo_table = geo_cols.get(table_name, {})

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
                att_name, iatt_name = row[0].lower(), row[0]
                comment_notes = [] # Holds Field notes, to be displayed in a Python comment.
                extra_params = {}  # Holds Field parameters such as 'db_column'.

                if ' ' in att_name:
                    extra_params['db_column'] = att_name
                    att_name = att_name.replace(' ', '')
                    comment_notes.append('Field renamed to remove spaces.')
                if keyword.iskeyword(att_name):
                    extra_params['db_column'] = att_name
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
                    if iatt_name in geo_table:
                        ## Customization for Geographic Columns ##
                        geo_col = geo_table[iatt_name]
                        field_type = self.geofield_mapping[geo_col['type'].lower()]
                        # Adding extra keyword arguments for the SRID and dimension (if not defaults).
                        dim, srid = geo_col.get('dim', 2), geo_col.get('srid', 4326)
                        if dim != 2: extra_params['dim'] = dim
                        if srid != 4326: extra_params['srid'] = srid
                    else:
                        try:
                            field_type = connection.introspection.data_types_reverse[row[1]]
                        except KeyError:
                            field_type = 'TextField'
                            comment_notes.append('This field type is a guess.')

                    # This is a hook for data_types_reverse to return a tuple of
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
            if table_name in geo_cols:
                yield '    objects = models.GeoManager()'
            yield '    class Meta:'
            yield '        db_table = %r' % table_name
            yield ''
