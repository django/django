from django.db.backends.creation import BaseDatabaseCreation
from django.utils.functional import cached_property


class DatabaseCreation(BaseDatabaseCreation):
    # This dictionary maps Field objects to their associated MySQL column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__ before being output.
    # If a column type is set to None, it won't be included in the output.
    _data_types = {
        'AutoField': 'integer AUTO_INCREMENT',
        'BinaryField': 'longblob',
        'BooleanField': 'bool',
        'CharField': 'varchar(%(max_length)s)',
        'CommaSeparatedIntegerField': 'varchar(%(max_length)s)',
        'DateField': 'date',
        'DateTimeField': 'datetime',
        'DecimalField': 'numeric(%(max_digits)s, %(decimal_places)s)',
        'FileField': 'varchar(%(max_length)s)',
        'FilePathField': 'varchar(%(max_length)s)',
        'FloatField': 'double precision',
        'IntegerField': 'integer',
        'BigIntegerField': 'bigint',
        'IPAddressField': 'char(15)',
        'GenericIPAddressField': 'char(39)',
        'NullBooleanField': 'bool',
        'OneToOneField': 'integer',
        'PositiveIntegerField': 'integer UNSIGNED',
        'PositiveSmallIntegerField': 'smallint UNSIGNED',
        'SlugField': 'varchar(%(max_length)s)',
        'SmallIntegerField': 'smallint',
        'TextField': 'longtext',
        'TimeField': 'time',
        'UUIDField': 'char(32)',
    }

    @cached_property
    def data_types(self):
        if self.connection.features.supports_microsecond_precision:
            return dict(self._data_types, DateTimeField='datetime(6)', TimeField='time(6)')
        else:
            return self._data_types

    def sql_table_creation_suffix(self):
        suffix = []
        test_settings = self.connection.settings_dict['TEST']
        if test_settings['CHARSET']:
            suffix.append('CHARACTER SET %s' % test_settings['CHARSET'])
        if test_settings['COLLATION']:
            suffix.append('COLLATE %s' % test_settings['COLLATION'])
        return ' '.join(suffix)

    def sql_for_inline_foreign_key_references(self, model, field, known_models, style):
        "All inline references are pending under MySQL"
        return [], True

    def sql_destroy_indexes_for_fields(self, model, fields, style):
        if len(fields) == 1 and fields[0].db_tablespace:
            tablespace_sql = self.connection.ops.tablespace_sql(fields[0].db_tablespace)
        elif model._meta.db_tablespace:
            tablespace_sql = self.connection.ops.tablespace_sql(model._meta.db_tablespace)
        else:
            tablespace_sql = ""
        if tablespace_sql:
            tablespace_sql = " " + tablespace_sql

        field_names = []
        qn = self.connection.ops.quote_name
        for f in fields:
            field_names.append(style.SQL_FIELD(qn(f.column)))

        index_name = "%s_%s" % (model._meta.db_table, self._digest([f.name for f in fields]))

        from ..utils import truncate_name

        return [
            style.SQL_KEYWORD("DROP INDEX") + " " +
            style.SQL_TABLE(qn(truncate_name(index_name, self.connection.ops.max_name_length()))) + " " +
            style.SQL_KEYWORD("ON") + " " +
            style.SQL_TABLE(qn(model._meta.db_table)) + ";",
        ]
