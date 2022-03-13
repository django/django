from django.core import checks
from django.db.backends.base.validation import BaseDatabaseValidation
from django.utils.version import get_docs_version


class DatabaseValidation(BaseDatabaseValidation):
    def check(self, **kwargs):
        issues = super().check(**kwargs)
        issues.extend(self._check_sql_mode(**kwargs))
        return issues

    def _check_sql_mode(self, **kwargs):
        if not (
            self.connection.sql_mode & {"STRICT_TRANS_TABLES", "STRICT_ALL_TABLES"}
        ):
            return [
                checks.Warning(
                    "%s Strict Mode is not set for database connection '%s'"
                    % (self.connection.display_name, self.connection.alias),
                    hint=(
                        "%s's Strict Mode fixes many data integrity problems in "
                        "%s, such as data truncation upon insertion, by "
                        "escalating warnings into errors. It is strongly "
                        "recommended you activate it. See: "
                        "https://docs.djangoproject.com/en/%s/ref/databases/"
                        "#mysql-sql-mode"
                        % (
                            self.connection.display_name,
                            self.connection.display_name,
                            get_docs_version(),
                        ),
                    ),
                    id="mysql.W002",
                )
            ]
        return []

    def check_field_type(self, field, field_type):
        """
        MySQL has the following field length restriction:
        No character (varchar) fields can have a length exceeding 255
        characters if they have a unique index on them.
        MySQL doesn't support a database index on some data types.
        """
        errors = []
        if (
            field_type.startswith("varchar")
            and field.unique
            and (field.max_length is None or int(field.max_length) > 255)
        ):
            errors.append(
                checks.Warning(
                    "%s may not allow unique CharFields to have a max_length "
                    "> 255." % self.connection.display_name,
                    obj=field,
                    hint=(
                        "See: https://docs.djangoproject.com/en/%s/ref/"
                        "databases/#mysql-character-fields" % get_docs_version()
                    ),
                    id="mysql.W003",
                )
            )

        if field.db_index and field_type.lower() in self.connection._limited_data_types:
            errors.append(
                checks.Warning(
                    "%s does not support a database index on %s columns."
                    % (self.connection.display_name, field_type),
                    hint=(
                        "An index won't be created. Silence this warning if "
                        "you don't care about it."
                    ),
                    obj=field,
                    id="fields.W162",
                )
            )
        return errors
