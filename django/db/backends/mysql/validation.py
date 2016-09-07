from django.core import checks
from django.db.backends.base.validation import BaseDatabaseValidation
from django.utils.version import get_docs_version


class DatabaseValidation(BaseDatabaseValidation):
    def check(self, **kwargs):
        issues = super(DatabaseValidation, self).check(**kwargs)
        issues.extend(self._check_sql_mode(**kwargs))
        return issues

    def _check_sql_mode(self, **kwargs):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT @@sql_mode")
            sql_mode = cursor.fetchone()
        modes = set(sql_mode[0].split(',') if sql_mode else ())
        if not (modes & {'STRICT_TRANS_TABLES', 'STRICT_ALL_TABLES'}):
            return [checks.Warning(
                "MySQL Strict Mode is not set for database connection '%s'" % self.connection.alias,
                hint="MySQL's Strict Mode fixes many data integrity problems in MySQL, "
                     "such as data truncation upon insertion, by escalating warnings into "
                     "errors. It is strongly recommended you activate it. See: "
                     "https://docs.djangoproject.com/en/%s/ref/databases/#mysql-sql-mode"
                     % (get_docs_version(),),
                id='mysql.W002',
            )]
        return []

    def check_field(self, field, **kwargs):
        """
        MySQL has the following field length restriction:
        No character (varchar) fields can have a length exceeding 255
        characters if they have a unique index on them.
        """
        from django.db import connection

        errors = super(DatabaseValidation, self).check_field(field, **kwargs)

        # Ignore any related fields.
        if getattr(field, 'remote_field', None) is None:
            field_type = field.db_type(connection)

            # Ignore any non-concrete fields
            if field_type is None:
                return errors

            if (field_type.startswith('varchar') and field.unique and
                    (field.max_length is None or int(field.max_length) > 255)):
                errors.append(
                    checks.Error(
                        'MySQL does not allow unique CharFields to have a max_length > 255.',
                        obj=field,
                        id='mysql.E001',
                    )
                )
        return errors
